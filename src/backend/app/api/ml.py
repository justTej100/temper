"""Read the latest forecast for an event, and kick off/poll training jobs.

Training never happens on a read (`GET .../ml` is a plain read of whatever was
last computed). `POST .../ml-jobs` queues a job and runs it via BackgroundTasks
(see ml_pipeline.py) since this build has no separate Celery worker.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_market_or_404, require_admin_token
from app.api.ml_pipeline import run_forecast_job
from app.db import get_session
from app.db.models import (
    CityModel,
    EdgeSnapshot,
    ForecastJob,
    JobStatus,
    JobType,
    ModelPrediction,
    TempBucket,
)

router = APIRouter(
    prefix="/events",
    tags=["Events - ML"],
)

_ACTIVE_STATUSES = [
    JobStatus.queued,
    JobStatus.fetching,
    JobStatus.training,
    JobStatus.evaluating,
]


def _job_out(job: ForecastJob) -> dict:
    return {
        "job_id": job.id,
        "market_id": job.market_id,
        "job_type": job.job_type,
        "status": job.status,
        "error_message": job.error_message,
        "attempts": job.attempts,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at,
    }


@router.get("/{event_slug}/ml")
async def get_event_ml(event_slug: str, session: Session = Depends(get_session)):
    market = get_market_or_404(event_slug, session)

    active_job = session.exec(
        select(ForecastJob).where(
            ForecastJob.market_id == market.id,
            ForecastJob.status.in_(_ACTIVE_STATUSES),
        )
    ).first()

    prediction = session.exec(
        select(ModelPrediction)
        .where(ModelPrediction.market_id == market.id)
        .order_by(ModelPrediction.generated_at.desc())
    ).first()

    if prediction is None:
        return {
            "event_slug": market.polymarket_slug,
            "has_prediction": False,
            "active_job": _job_out(active_job) if active_job else None,
            "message": (
                "A forecast job is already in progress for this event."
                if active_job
                else "No forecast yet. POST to /events/{event_slug}/ml-jobs to request one."
            ),
        }

    city_model = (
        session.get(CityModel, prediction.city_model_id) if prediction.city_model_id else None
    )

    edge_rows = session.exec(
        select(EdgeSnapshot, TempBucket)
        .join(TempBucket, EdgeSnapshot.bucket_id == TempBucket.id)
        .where(EdgeSnapshot.market_id == market.id)
        .order_by(EdgeSnapshot.generated_at.desc())
    ).all()
    latest_per_bucket: dict[int, tuple[EdgeSnapshot, TempBucket]] = {}
    for edge, bucket in edge_rows:
        latest_per_bucket.setdefault(bucket.id, (edge, bucket))

    return {
        "event_slug": market.polymarket_slug,
        "has_prediction": True,
        "active_job": _job_out(active_job) if active_job else None,
        "generated_at": prediction.generated_at,
        "target_date": prediction.target_date,
        "point_forecast_c": prediction.point_forecast_c,
        "residual_rmse": prediction.residual_rmse,
        "calibration_method": prediction.calibration_method,
        "forecast_dates": prediction.forecast_dates,
        "forecast_temps": prediction.forecast_temps,
        "bucket_probabilities": prediction.bucket_probs,
        "model": (
            {
                "model_type": city_model.model_type,
                "mae": city_model.mae,
                "rmse": city_model.rmse,
                "bias": city_model.bias,
                "data_start": city_model.data_start,
                "data_end": city_model.data_end,
                "backtest_folds": city_model.backtest_folds,
                "target_horizon_days": city_model.target_horizon_days,
                "calibration_sample_size": city_model.calibration_sample_size,
                "trained_at": city_model.trained_at,
                "mlflow_run_id": city_model.mlflow_run_id,
            }
            if city_model
            else None
        ),
        "edges": [
            {
                "bucket_label": bucket.label,
                "model_prob": edge.model_prob,
                "market_prob": edge.market_prob,
                "edge": edge.edge,
                "generated_at": edge.generated_at,
            }
            for edge, bucket in latest_per_bucket.values()
        ],
    }


@router.post("/{event_slug}/ml-jobs", status_code=202, dependencies=[Depends(require_admin_token)])
async def create_ml_job(
    event_slug: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    market = get_market_or_404(event_slug, session)
    if not market.supported:
        raise HTTPException(
            status_code=422,
            detail=market.unsupported_reason
            or "This event's resolution station isn't verified, so it can't be forecast",
        )

    existing = session.exec(
        select(ForecastJob).where(
            ForecastJob.market_id == market.id,
            ForecastJob.job_type == JobType.forecast,
            ForecastJob.status.in_(_ACTIVE_STATUSES),
        )
    ).first()
    if existing:
        return {**_job_out(existing), "deduplicated": True}

    job = ForecastJob(market_id=market.id, job_type=JobType.forecast, status=JobStatus.queued)
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(run_forecast_job, job.id)

    return {**_job_out(job), "deduplicated": False}


@router.get("/{event_slug}/ml-jobs/{job_id}")
async def get_ml_job(event_slug: str, job_id: int, session: Session = Depends(get_session)):
    market = get_market_or_404(event_slug, session)
    job = session.get(ForecastJob, job_id)
    if job is None or job.market_id != market.id:
        raise HTTPException(status_code=404, detail="Job not found for this event")
    return _job_out(job)
