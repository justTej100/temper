import logging
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.celery_app import celery_app
from app.db import engine
from app.models import ForecastJob, JobStatus, JobType, Market
from app.services import create_forecast_job, run_forecast_for_market, sync_markets

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.sync_polymarket_markets")
def sync_polymarket_markets(self, job_id: int):
    with Session(engine) as session:
        job = session.get(ForecastJob, job_id)
        if not job or job.status == JobStatus.complete:
            return {"job_id": job_id, "status": "complete"}
        job.celery_task_id = self.request.id or ""
        job.status = JobStatus.fetching
        job.attempts += 1
        session.add(job)
        session.commit()
        try:
            count = sync_markets(session)
            job.status = JobStatus.complete
            job.completed_at = job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            logger.info("Synced %s high-temperature markets", count)
            return {"job_id": job_id, "status": "complete", "synced": count}
        except Exception as exc:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            job.completed_at = job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            raise


@celery_app.task(bind=True, name="app.tasks.run_forecast_pipeline", max_retries=2)
def run_forecast_pipeline(self, job_id: int):
    with Session(engine) as session:
        job = session.get(ForecastJob, job_id)
        if job:
            job.celery_task_id = self.request.id or ""
            job.attempts += 1
            session.add(job)
            session.commit()
        try:
            run_forecast_for_market(session, job_id)
            return {"job_id": job_id, "status": "complete"}
        except Exception as exc:
            if self.request.retries < self.max_retries:
                job = session.get(ForecastJob, job_id)
                if job:
                    job.status = JobStatus.queued
                    job.error_message = f"Retrying after: {exc}"
                    job.completed_at = None
                    session.add(job)
                    session.commit()
            raise self.retry(exc=exc, countdown=30) from exc


@celery_app.task(name="app.tasks.run_scheduled_workflow")
def run_scheduled_workflow():
    """Sync once, then forecast each supported market using reusable city models."""
    with Session(engine) as session:
        sync_job = ForecastJob(job_type=JobType.scheduled, status=JobStatus.fetching)
        session.add(sync_job)
        session.commit()
        session.refresh(sync_job)
        try:
            count = sync_markets(session)
            market_ids = session.exec(
                select(Market.id)
                .where(
                    Market.active == True,
                    Market.supported == True,
                )
                .order_by(col(Market.target_date))
            ).all()
            queued = 0
            for market_id in market_ids:
                job, created = create_forecast_job(session, market_id)
                if created:
                    run_forecast_pipeline.delay(job.id)
                    queued += 1
            sync_job.status = JobStatus.complete
            sync_job.completed_at = datetime.now(UTC)
            session.add(sync_job)
            session.commit()
            return {"synced": count, "queued": queued}
        except Exception as exc:
            sync_job.status = JobStatus.failed
            sync_job.error_message = str(exc)
            sync_job.completed_at = datetime.now(UTC)
            session.add(sync_job)
            session.commit()
            raise
