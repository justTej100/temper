import logging

from sqlmodel import Session

from app.celery_app import celery_app
from app.db import engine
from app.models import ForecastJob, JobStatus
from app.services import run_forecast_for_market, sync_markets

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.sync_polymarket_markets")
def sync_polymarket_markets():
    with Session(engine) as session:
        count = sync_markets(session)
        logger.info("Synced %s weather markets", count)
        return {"synced": count}


@celery_app.task(bind=True, name="app.tasks.run_forecast_pipeline", max_retries=1)
def run_forecast_pipeline(self, job_id: int):
    with Session(engine) as session:
        job = session.get(ForecastJob, job_id)
        if job:
            job.celery_task_id = self.request.id or ""
            session.add(job)
            session.commit()
        try:
            run_forecast_for_market(session, job_id)
            return {"job_id": job_id, "status": "complete"}
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30) from exc
