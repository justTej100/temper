from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import ForecastJob, PricePoint, Product, ProductModel


def get_cached_best_model(product: Product) -> ProductModel | None:
    """Return the best model if trained recently enough."""
    cutoff = timezone.now() - timedelta(hours=settings.MODEL_CACHE_TTL_HOURS)
    return (
        ProductModel.objects.filter(
            product=product,
            is_best=True,
            is_comparable=True,
            trained_at__gte=cutoff,
        )
        .order_by("-trained_at")
        .first()
    )


def save_price_points(product: Product, records) -> int:
    """Bulk save price records, skipping duplicates."""
    created = 0
    for record in records:
        recorded_at = record.recorded_at
        if hasattr(recorded_at, "tzinfo") and recorded_at.tzinfo is not None:
            recorded_at = recorded_at.replace(tzinfo=None)
        # Normalize to start of day for consistent deduplication
        if hasattr(recorded_at, "replace"):
            recorded_at = recorded_at.replace(hour=0, minute=0, second=0, microsecond=0)
        _, was_created = PricePoint.objects.update_or_create(
            product=product,
            recorded_at=recorded_at,
            defaults={"price": record.price},
        )
        if was_created:
            created += 1
    product.last_scraped_at = timezone.now()
    product.save(update_fields=["last_scraped_at"])
    return created


def save_model_results(product: Product, job: ForecastJob, training_output) -> ProductModel:
    """Persist all model results and flag the best one."""
    from forecasting.storage import save_model, save_prophet_model

    ProductModel.objects.filter(product=product, is_best=True).update(is_best=False)

    best_db_model = None
    for result in training_output.results:
        if result.model_type == "prophet" and result.fitted_model:
            file_path = save_prophet_model(result.fitted_model, product.id)
        elif result.fitted_model:
            file_path = save_model(result.fitted_model, product.id, result.model_type)
        else:
            continue

        is_best = (
            training_output.best_model is not None
            and result.model_type == training_output.best_model.model_type
        )
        db_model = ProductModel.objects.create(
            product=product,
            job=job,
            model_type=result.model_type,
            file_path=file_path,
            params=result.params,
            mae=result.mae,
            mape=result.mape,
            rmse=result.rmse,
            mlflow_run_id=result.mlflow_run_id,
            is_best=is_best,
            is_comparable=result.is_comparable,
        )
        if is_best:
            best_db_model = db_model

    return best_db_model
