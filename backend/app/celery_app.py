from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "temperature_predictor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=settings.task_soft_time_limit_seconds,
    task_time_limit=settings.task_time_limit_seconds,
    beat_schedule={
        "temperature-predictor-workflow": {
            "task": "app.tasks.run_scheduled_workflow",
            "schedule": settings.schedule_minutes * 60,
        },
    },
)
