import logging

from celery import shared_task
from django.utils import timezone

from forecasting.data_sources.base import get_data_source
from forecasting.dip_model import predict_dip_for_product, train_global_dip_model
from forecasting.trainer import train_all_models

from .models import ForecastJob
from .services import save_model_results, save_price_points

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_forecast_pipeline(self, job_id: int):
    """Fetch price history, train models, and store results."""
    job = ForecastJob.objects.select_related("product").get(id=job_id)
    product = job.product

    try:
        job.status = ForecastJob.Status.FETCHING
        job.celery_task_id = self.request.id or ""
        job.save(update_fields=["status", "celery_task_id"])

        source = get_data_source()
        records = source.fetch_price_history(product.external_id)
        save_price_points(product, records)
        train_global_dip_model()

        job.status = ForecastJob.Status.TRAINING
        job.save(update_fields=["status"])

        price_points = product.price_points.all()
        training_output = train_all_models(price_points, product.id, product.name)
        save_model_results(product, job, training_output)
        predict_dip_for_product(product, force_refresh=True)

        job.status = ForecastJob.Status.COMPLETE
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])

        return {"job_id": job_id, "status": "complete"}

    except Exception as exc:
        logger.exception("Forecast pipeline failed for job %s", job_id)
        job.status = ForecastJob.Status.FAILED
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
        raise self.retry(exc=exc) from exc