"""End-to-end forecast pipeline: fetch history, train, calibrate, persist.

There is no Celery worker in this build (see requirements.txt / Dockerfile) so
this runs via FastAPI `BackgroundTasks` in-process instead of a separate queue
consumer. It opens its own DB session because it executes after the request
that spawned it has already returned.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pandas as pd
from sqlmodel import Session, select

from app.db.db import engine
from app.db.models import (
    City,
    CityModel,
    EdgeSnapshot,
    ForecastJob,
    JobStatus,
    Market,
    ModelPrediction,
    Observation,
    TempBucket,
)
from forecasting import trainer
from forecasting.buckets import bucket_probabilities
from forecasting.data_sources.open_meteo import fetch_daily_history

logger = logging.getLogger(__name__)


def _set_status(session: Session, job: ForecastJob, status: JobStatus, *, error: str = "") -> None:
    job.status = status
    job.error_message = error
    job.updated_at = datetime.now(UTC)
    if status in {JobStatus.complete, JobStatus.failed}:
        job.completed_at = datetime.now(UTC)
    session.add(job)
    session.commit()


def run_forecast_job(job_id: int) -> None:
    with Session(engine) as session:
        job = session.get(ForecastJob, job_id)
        if job is None:
            logger.error("Forecast job %s vanished before it could run", job_id)
            return
        market = session.get(Market, job.market_id)
        if market is None:
            _set_status(session, job, JobStatus.failed, error="Market no longer exists")
            return
        city = session.get(City, market.city_id)
        if city is None:
            _set_status(session, job, JobStatus.failed, error="City no longer exists")
            return

        try:
            job.attempts += 1
            _set_status(session, job, JobStatus.fetching)
            history = fetch_daily_history(city.latitude, city.longitude, city.timezone)

            existing_obs = {
                obs.observed_on: obs
                for obs in session.exec(
                    select(Observation).where(
                        Observation.city_id == city.id,
                        Observation.source == "open-meteo",
                    )
                ).all()
            }
            for row in history.itertuples(index=False):
                record = existing_obs.get(row.observed_on)
                if record is None:
                    record = Observation(
                        city_id=city.id, observed_on=row.observed_on, source="open-meteo"
                    )
                record.high_c = row.high_c
                session.add(record)
            session.commit()

            series = pd.Series(
                history.set_index("observed_on")["high_c"].astype(float)
            )

            _set_status(session, job, JobStatus.training)
            output = trainer.train_temperature_models(
                series, city.id, city.name, market.target_date, station=city.icao
            )

            _set_status(session, job, JobStatus.evaluating)
            point_forecast = float(output.forecast.iloc[-1])

            buckets = session.exec(
                select(TempBucket).where(
                    TempBucket.market_id == market.id, TempBucket.active == True
                )
            ).all()
            bucket_dicts = [
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
                point_forecast, output.residual_rmse, bucket_dicts, output.calibration_errors
            )

            model_path = trainer.save_model_artifact(
                output.best_model.fitted_model, city.id, output.best_model.model_type
            )

            city_model = CityModel(
                city_id=city.id,
                job_id=job.id,
                model_type=output.best_model.model_type,
                file_path=model_path,
                artifact_uri=output.best_model.artifact_uri,
                params=output.best_model.params,
                metrics={
                    "mae": output.best_model.mae,
                    "rmse": output.best_model.rmse,
                    "bias": output.best_model.bias,
                },
                mae=output.best_model.mae,
                rmse=output.best_model.rmse,
                bias=output.best_model.bias,
                data_start=output.series.index.min().date(),
                data_end=output.series.index.max().date(),
                dataset_fingerprint=output.dataset_fingerprint,
                target_horizon_days=output.horizon_days,
                backtest_folds=output.fold_count,
                calibration_sample_size=len(output.calibration_errors),
                mlflow_run_id=output.best_model.mlflow_run_id,
                is_best=True,
                is_comparable=output.best_model.is_comparable,
            )
            session.add(city_model)
            session.commit()
            session.refresh(city_model)

            prediction = ModelPrediction(
                market_id=market.id,
                city_model_id=city_model.id,
                target_date=market.target_date,
                point_forecast_c=point_forecast,
                residual_rmse=output.residual_rmse,
                calibration_method=output.calibration_method,
                mlflow_run_id=output.best_model.mlflow_run_id,
                bucket_probs=probabilities,
                forecast_dates=[ts.date().isoformat() for ts in output.forecast.index],
                forecast_temps=[float(v) for v in output.forecast.to_numpy()],
            )
            session.add(prediction)

            for bucket in buckets:
                model_prob = probabilities.get(bucket.label, 0.0)
                session.add(
                    EdgeSnapshot(
                        market_id=market.id,
                        bucket_id=bucket.id,
                        model_prob=model_prob,
                        market_prob=bucket.yes_price,
                        edge=model_prob - bucket.yes_price,
                    )
                )
            session.commit()

            _set_status(session, job, JobStatus.complete)
        except Exception as exc:  # noqa: BLE001 - persist failure for polling clients
            logger.exception("Forecast job %s failed", job_id)
            session.rollback()
            failed_job = session.get(ForecastJob, job_id)
            if failed_job is not None:
                _set_status(session, failed_job, JobStatus.failed, error=str(exc)[:500])
