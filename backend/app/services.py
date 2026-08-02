"""Business logic: sync markets, ingest obs, run forecast pipeline."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
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
from forecasting.trainer import save_model_artifact, train_temperature_models

logger = logging.getLogger(__name__)


def sync_markets(session: Session) -> int:
    events = fetch_weather_events()
    count = 0
    for event in events:
        station = event["station"]
        if (station.get("lat") == 0.0 and station.get("lon") == 0.0) or not station.get("lat"):
            geo = geocode_city(event["city_raw"])
            if geo:
                station = {**station, **geo}

        city = session.exec(
            select(City).where(City.name == station["name"])
        ).first()
        if not city:
            city = City(
                name=station["name"],
                country=station.get("country") or "",
                latitude=float(station["lat"]),
                longitude=float(station["lon"]),
                icao=station.get("icao") or "",
            )
            session.add(city)
            session.commit()
            session.refresh(city)

        market = session.exec(
            select(Market).where(Market.polymarket_slug == event["slug"])
        ).first()
        if not market:
            market = Market(
                city_id=city.id,
                polymarket_event_id=event["event_id"],
                polymarket_slug=event["slug"],
                question=event["question"],
                temp_type=TempType(event["temp_type"]),
                target_date=event["target_date"],
                volume=event["volume"],
                url=event["url"],
                active=True,
                last_synced_at=datetime.utcnow(),
            )
            session.add(market)
            session.commit()
            session.refresh(market)
        else:
            market.volume = event["volume"]
            market.active = True
            market.last_synced_at = datetime.utcnow()
            market.question = event["question"]
            session.add(market)
            session.commit()

        # Replace buckets
        existing = session.exec(select(TempBucket).where(TempBucket.market_id == market.id)).all()
        for b in existing:
            session.delete(b)
        session.commit()

        for bucket in event["buckets"]:
            session.add(
                TempBucket(
                    market_id=market.id,
                    label=bucket["label"] or f"{bucket.get('temp_c')}°C",
                    temp_c=bucket.get("temp_c"),
                    is_or_higher=bool(bucket.get("is_or_higher")),
                    is_or_lower=bool(bucket.get("is_or_lower")),
                    token_id=bucket.get("token_id") or "",
                    yes_price=float(bucket.get("yes_price") or 0),
                    updated_at=datetime.utcnow(),
                )
            )
        session.commit()
        count += 1
    return count


def ingest_city_observations(session: Session, city: City) -> int:
    if city.latitude == 0 and city.longitude == 0:
        return 0
    df = fetch_daily_history(city.latitude, city.longitude)
    created = 0
    for row in df.itertuples(index=False):
        existing = session.exec(
            select(Observation).where(
                Observation.city_id == city.id,
                Observation.observed_on == row.observed_on,
            )
        ).first()
        if existing:
            existing.high_c = row.high_c
            existing.low_c = row.low_c
            session.add(existing)
        else:
            session.add(
                Observation(
                    city_id=city.id,
                    observed_on=row.observed_on,
                    high_c=row.high_c,
                    low_c=row.low_c,
                    source="open-meteo",
                )
            )
            created += 1
    session.commit()
    return created


def run_forecast_for_market(session: Session, job_id: int) -> None:
    job = session.get(ForecastJob, job_id)
    if not job:
        return
    market = session.get(Market, job.market_id)
    if not market:
        job.status = JobStatus.failed
        job.error_message = "Market not found"
        session.add(job)
        session.commit()
        return

    city = session.get(City, market.city_id)
    try:
        job.status = JobStatus.fetching
        session.add(job)
        session.commit()

        ingest_city_observations(session, city)

        job.status = JobStatus.training
        session.add(job)
        session.commit()

        obs = session.exec(
            select(Observation)
            .where(Observation.city_id == city.id)
            .order_by(col(Observation.observed_on))
        ).all()
        if not obs:
            raise ValueError("No observations")

        values = []
        dates = []
        for o in obs:
            temp = o.high_c if market.temp_type == TempType.high else o.low_c
            if temp is None:
                continue
            values.append(float(temp))
            dates.append(pd.Timestamp(o.observed_on))
        series = pd.Series(values, index=pd.DatetimeIndex(dates))

        training = train_temperature_models(
            series, city.id, city.name, market.temp_type.value
        )

        # Clear previous best flags for this city+type
        prior = session.exec(
            select(CityModel).where(
                CityModel.city_id == city.id,
                CityModel.temp_type == market.temp_type,
                CityModel.is_best == True,  # noqa: E712
            )
        ).all()
        for p in prior:
            p.is_best = False
            session.add(p)

        best_db = None
        for result in training.results:
            path = ""
            if result.fitted_model is not None:
                path = save_model_artifact(result.fitted_model, city.id, result.model_type)
            is_best = training.best_model and result.model_type == training.best_model.model_type
            row = CityModel(
                city_id=city.id,
                job_id=job.id,
                temp_type=market.temp_type,
                model_type=result.model_type,
                file_path=path,
                params=result.params,
                mae=result.mae,
                mape=result.mape,
                rmse=result.rmse,
                mlflow_run_id=result.mlflow_run_id,
                is_best=bool(is_best),
                is_comparable=result.is_comparable,
            )
            session.add(row)
            if is_best:
                best_db = row
        session.commit()
        if best_db:
            session.refresh(best_db)

        buckets = session.exec(
            select(TempBucket).where(TempBucket.market_id == market.id)
        ).all()
        point = float(training.forecast.iloc[0]) if training.forecast is not None and len(training.forecast) else float(series.iloc[-1])
        # Prefer forecast for target_date if present
        if training.forecast is not None:
            target_ts = pd.Timestamp(market.target_date)
            if target_ts in training.forecast.index:
                point = float(training.forecast.loc[target_ts])
            else:
                # nearest future point
                future = training.forecast[training.forecast.index >= target_ts]
                if len(future):
                    point = float(future.iloc[0])
                else:
                    point = float(training.forecast.iloc[-1])

        probs = bucket_probabilities(
            point,
            training.residual_rmse,
            [
                {
                    "label": b.label,
                    "temp_c": b.temp_c,
                    "is_or_higher": b.is_or_higher,
                    "is_or_lower": b.is_or_lower,
                }
                for b in buckets
            ],
        )

        pred = ModelPrediction(
            market_id=market.id,
            city_model_id=best_db.id if best_db else None,
            point_forecast_c=point,
            residual_rmse=training.residual_rmse,
            bucket_probs=probs,
            forecast_dates=[d.strftime("%Y-%m-%d") for d in training.forecast.index]
            if training.forecast is not None
            else [],
            forecast_temps=[round(float(v), 2) for v in training.forecast.values]
            if training.forecast is not None
            else [],
        )
        session.add(pred)

        # Edges
        old_edges = session.exec(
            select(EdgeSnapshot).where(EdgeSnapshot.market_id == market.id)
        ).all()
        for e in old_edges:
            session.delete(e)

        threshold = get_settings().edge_threshold
        for b in buckets:
            model_p = float(probs.get(b.label, 0.0))
            market_p = float(b.yes_price)
            edge = model_p - market_p
            session.add(
                EdgeSnapshot(
                    market_id=market.id,
                    bucket_id=b.id,
                    model_prob=model_p,
                    market_prob=market_p,
                    edge=edge,
                )
            )
            _ = threshold  # used by API filter

        job.status = JobStatus.complete
        job.completed_at = datetime.utcnow()
        session.add(job)
        session.commit()
    except Exception as exc:
        logger.exception("Forecast failed for job %s", job_id)
        job.status = JobStatus.failed
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()
        session.add(job)
        session.commit()
        raise
