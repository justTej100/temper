"""Idempotent market sync, observation ingestion, and forecast orchestration."""

from __future__ import annotations

import logging
import pickle
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.config import get_settings
from app.models import (
    City,
    CityModel,
    EdgeSnapshot,
    ForecastJob,
    JobStatus,
    Market,
    ModelPrediction,
    Observation,
    TempBucket,
    TempType,
)
from forecasting.buckets import bucket_probabilities
from forecasting.data_sources.open_meteo import fetch_daily_history, geocode_city
from forecasting.data_sources.polymarket import fetch_weather_events
from forecasting.trainer import (
    forecast_fitted_model,
    save_model_artifact,
    train_temperature_models,
)

logger = logging.getLogger(__name__)
ACTIVE_JOB_STATUSES = {
    JobStatus.queued,
    JobStatus.fetching,
    JobStatus.training,
    JobStatus.evaluating,
}


def _set_job(
    session: Session,
    job: ForecastJob,
    status: JobStatus,
    *,
    error: str = "",
    complete: bool = False,
) -> None:
    job.status = status
    job.error_message = error
    job.updated_at = datetime.now(UTC)
    if complete:
        job.completed_at = datetime.now(UTC)
    session.add(job)
    session.commit()


def create_forecast_job(session: Session, market_id: int) -> tuple[ForecastJob, bool]:
    active = session.exec(
        select(ForecastJob)
        .where(
            ForecastJob.market_id == market_id,
            col(ForecastJob.status).in_(list(ACTIVE_JOB_STATUSES)),
        )
        .order_by(col(ForecastJob.created_at).desc())
    ).first()
    if active:
        return active, False
    job = ForecastJob(market_id=market_id, status=JobStatus.queued)
    session.add(job)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(ForecastJob).where(
                ForecastJob.market_id == market_id,
                col(ForecastJob.status).in_(list(ACTIVE_JOB_STATUSES)),
            )
        ).first()
        if existing:
            return existing, False
        raise
    session.refresh(job)
    return job, True


def sync_markets(session: Session) -> int:
    events = fetch_weather_events()
    synced_event_ids: set[str] = set()
    synced_at = datetime.now(UTC)
    for event in events:
        station = dict(event["station"])
        if station.get("lat") is None or station.get("lon") is None:
            fallback = geocode_city(event["city_raw"])
            if not fallback:
                logger.warning(
                    "Skipping market %s: city fallback could not be validated",
                    event["event_id"],
                )
                continue
            station.update(fallback)
            event["supported"] = False
            event["unsupported_reason"] = (
                "Geocoded grid location is not verified against the resolution station"
            )

        city = session.exec(
            select(City).where(
                City.name == station["name"],
                City.country == (station.get("country") or ""),
            )
        ).first()
        if not city:
            city = City(
                name=station["name"],
                country=station.get("country") or "",
                latitude=float(station["lat"]),
                longitude=float(station["lon"]),
                icao=station.get("icao") or "",
                timezone=station["timezone"],
                resolution_source=station.get("resolution_source") or "",
                resolution_verified=bool(station.get("resolution_verified")),
            )
            session.add(city)
            session.flush()
        else:
            city.latitude = float(station["lat"])
            city.longitude = float(station["lon"])
            city.icao = station.get("icao") or city.icao
            city.timezone = station["timezone"]
            city.resolution_source = station.get("resolution_source") or ""
            city.resolution_verified = bool(station.get("resolution_verified"))
        assert city.id is not None

        market = session.exec(
            select(Market).where(
                Market.polymarket_event_id == event["event_id"]
            )
        ).first()
        if not market:
            market = Market(
                city_id=city.id,
                polymarket_event_id=event["event_id"],
                polymarket_slug=event["slug"],
                target_date=event["target_date"],
            )
        market.city_id = city.id
        market.polymarket_slug = event["slug"]
        market.question = event["question"]
        market.temp_type = TempType.high
        market.target_date = event["target_date"]
        market.volume = event["volume"]
        market.url = event["url"]
        market.active = True
        market.supported = bool(event["supported"])
        market.unsupported_reason = event["unsupported_reason"]
        market.resolution_source = event["resolution_source"]
        market.resolution_station = event["resolution_station"]
        market.last_synced_at = synced_at
        session.add(market)
        session.flush()
        assert market.id is not None

        current_bucket_ids: set[int] = set()
        for data in event["buckets"]:
            token_id = data.get("token_id") or ""
            query = select(TempBucket).where(TempBucket.market_id == market.id)
            query = query.where(
                TempBucket.token_id == token_id
                if token_id
                else TempBucket.label == data["label"]
            )
            bucket = session.exec(query).first()
            if not bucket:
                bucket = TempBucket(market_id=market.id, label=data["label"])
            bucket.label = data["label"]
            bucket.temp_c = data["temp_c"]
            bucket.source_unit = data["source_unit"]
            bucket.bucket_width_c = data["bucket_width_c"]
            bucket.is_or_higher = bool(data["is_or_higher"])
            bucket.is_or_lower = bool(data["is_or_lower"])
            bucket.token_id = token_id
            bucket.yes_price = float(data["yes_price"])
            bucket.active = True
            bucket.updated_at = synced_at
            session.add(bucket)
            session.flush()
            assert bucket.id is not None
            current_bucket_ids.add(bucket.id)

        stale_buckets = session.exec(
            select(TempBucket).where(
                TempBucket.market_id == market.id,
                TempBucket.active == True,
            )
        ).all()
        for bucket in stale_buckets:
            if bucket.id not in current_bucket_ids:
                bucket.active = False
                session.add(bucket)
        synced_event_ids.add(event["event_id"])

    if synced_event_ids:
        active_markets = session.exec(
            select(Market).where(Market.active == True)
        ).all()
        for market in active_markets:
            if market.polymarket_event_id not in synced_event_ids:
                market.active = False
                session.add(market)
    session.commit()
    return len(synced_event_ids)


def ingest_city_observations(session: Session, city: City) -> int:
    frame = fetch_daily_history(city.latitude, city.longitude, city.timezone)
    created = 0
    for row in frame.itertuples(index=False):
        observation = session.exec(
            select(Observation).where(
                Observation.city_id == city.id,
                Observation.observed_on == row.observed_on,
                Observation.source == city.data_source,
            )
        ).first()
        if not observation:
            observation = Observation(
                city_id=city.id,
                observed_on=row.observed_on,
                high_c=float(row.high_c),
                source=city.data_source,
            )
            created += 1
        else:
            observation.high_c = float(row.high_c)
        session.add(observation)
    session.commit()
    return created


def _history(session: Session, city_id: int) -> pd.Series:
    observations = session.exec(
        select(Observation)
        .where(Observation.city_id == city_id)
        .order_by(col(Observation.observed_on))
    ).all()
    return pd.Series(
        [float(item.high_c) for item in observations],
        index=pd.DatetimeIndex([item.observed_on for item in observations]),
        dtype=float,
    )


def _latest_reusable_model(
    session: Session, city_id: int, last_observed_on
) -> CityModel | None:
    cutoff = datetime.now(UTC) - timedelta(
        hours=get_settings().model_cache_ttl_hours
    )
    model = session.exec(
        select(CityModel)
        .where(
            CityModel.city_id == city_id,
            CityModel.temp_type == TempType.high,
            CityModel.is_best == True,
            CityModel.trained_at >= cutoff,
            CityModel.data_end == last_observed_on,
        )
        .order_by(col(CityModel.trained_at).desc())
    ).first()
    if model and model.file_path and Path(model.file_path).is_file():
        return model
    return None


def run_forecast_for_market(session: Session, job_id: int) -> None:
    job = session.get(ForecastJob, job_id)
    if not job or job.status == JobStatus.complete:
        return
    market = session.get(Market, job.market_id) if job.market_id else None
    if not market:
        _set_job(session, job, JobStatus.failed, error="Market not found", complete=True)
        return
    if not market.active or not market.supported:
        reason = market.unsupported_reason or "Market is inactive or source-ambiguous"
        _set_job(session, job, JobStatus.failed, error=reason, complete=True)
        return
    city = session.get(City, market.city_id)
    if not city:
        _set_job(session, job, JobStatus.failed, error="City not found", complete=True)
        return
    assert city.id is not None

    try:
        _set_job(session, job, JobStatus.fetching)
        ingest_city_observations(session, city)
        series = _history(session, city.id)
        if series.empty:
            raise ValueError("No high-temperature observations are available")
        last_observed_on = series.index[-1].date()

        _set_job(session, job, JobStatus.training)
        reusable = _latest_reusable_model(session, city.id, last_observed_on)
        training = None
        if reusable:
            model = pickle.loads(Path(reusable.file_path).read_bytes())
            forecast = forecast_fitted_model(
                model, reusable.model_type, last_observed_on, market.target_date
            )
            calibration_errors = list(
                (reusable.metrics or {}).get("calibration_errors") or []
            )
            residual_rmse = float(reusable.rmse or 1.0)
            best_db = reusable
            calibration_method = (
                "empirical" if len(calibration_errors) >= 20 else "gaussian-fallback"
            )
        else:
            training = train_temperature_models(
                series,
                city.id,
                city.name,
                market.target_date,
                station=city.icao,
            )
            for prior in session.exec(
                select(CityModel).where(
                    CityModel.city_id == city.id,
                    CityModel.is_best == True,
                )
            ).all():
                prior.is_best = False
                session.add(prior)

            best_db = None
            assert training.series is not None
            for result in training.results:
                selected = result is training.best_model
                path = (
                    save_model_artifact(result.fitted_model, city.id, result.model_type)
                    if selected
                    else ""
                )
                row = CityModel(
                    city_id=city.id,
                    job_id=job.id,
                    temp_type=TempType.high,
                    model_type=result.model_type,
                    file_path=path,
                    artifact_uri=result.artifact_uri,
                    params=result.params,
                    metrics={
                        "mae": result.mae,
                        "rmse": result.rmse,
                        "bias": result.bias,
                        "calibration_errors": result.errors,
                        "candidate_failures": training.candidate_failures,
                    },
                    mae=result.mae,
                    rmse=result.rmse,
                    bias=result.bias,
                    data_start=training.series.index[0].date(),
                    data_end=training.series.index[-1].date(),
                    dataset_fingerprint=training.dataset_fingerprint,
                    target_horizon_days=training.horizon_days,
                    backtest_folds=training.fold_count,
                    calibration_sample_size=len(result.errors),
                    mlflow_run_id=result.mlflow_run_id,
                    is_best=selected,
                    is_comparable=result.is_comparable,
                )
                session.add(row)
                if selected:
                    best_db = row
            session.commit()
            if not best_db:
                raise ValueError("No selected model was persisted")
            session.refresh(best_db)
            forecast = training.forecast
            calibration_errors = training.calibration_errors
            residual_rmse = training.residual_rmse
            calibration_method = training.calibration_method

        assert best_db is not None
        assert forecast is not None
        _set_job(session, job, JobStatus.evaluating)
        if market.target_date not in [item.date() for item in forecast.index]:
            raise ValueError("Forecast does not contain the exact target date")
        point = float(forecast.loc[pd.Timestamp(market.target_date)])
        buckets = session.exec(
            select(TempBucket).where(
                TempBucket.market_id == market.id,
                TempBucket.active == True,
            )
        ).all()
        bucket_data = [
            {
                "label": bucket.label,
                "temp_c": bucket.temp_c,
                "bucket_width_c": bucket.bucket_width_c,
                "is_or_higher": bucket.is_or_higher,
                "is_or_lower": bucket.is_or_lower,
            }
            for bucket in buckets
        ]
        probabilities = bucket_probabilities(
            point, residual_rmse, bucket_data, calibration_errors
        )
        if not probabilities or abs(sum(probabilities.values()) - 1.0) > 1e-9:
            raise ValueError("Bucket probabilities failed normalization")

        prediction = ModelPrediction(
            market_id=market.id,
            city_model_id=best_db.id,
            target_date=market.target_date,
            point_forecast_c=point,
            residual_rmse=residual_rmse,
            calibration_method=calibration_method,
            mlflow_run_id=best_db.mlflow_run_id,
            bucket_probs=probabilities,
            forecast_dates=[item.strftime("%Y-%m-%d") for item in forecast.index],
            forecast_temps=[round(float(value), 3) for value in forecast.values],
        )
        session.add(prediction)
        session.flush()
        for bucket in buckets:
            model_probability = float(probabilities.get(bucket.label, 0.0))
            session.add(
                EdgeSnapshot(
                    market_id=market.id,
                    bucket_id=bucket.id,
                    model_prob=model_probability,
                    market_prob=float(bucket.yes_price),
                    edge=model_probability - float(bucket.yes_price),
                )
            )
        _set_job(session, job, JobStatus.complete, complete=True)
    except Exception as exc:
        logger.exception("Forecast job %s failed", job_id)
        _set_job(session, job, JobStatus.failed, error=str(exc), complete=True)
        raise
