from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    source_url = models.URLField(blank=True, default="")
    external_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class PricePoint(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_points")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField(db_index=True)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["recorded_at"]
        unique_together = [("product", "recorded_at")]

    def __str__(self):
        return f"{self.product.name}: ${self.price} @ {self.recorded_at.date()}"


class ForecastJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        FETCHING = "fetching", "Fetching price history"
        TRAINING = "training", "Training models"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="jobs")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.pk} for {self.product.name} ({self.status})"


class ProductModel(models.Model):
    MODEL_TYPES = [
        ("arima", "ARIMA"),
        ("sarima", "SARIMA"),
        ("arimax", "ARIMAX"),
        ("sarimax", "SARIMAX"),
        ("prophet", "Prophet"),
        ("garch", "GARCH"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="models")
    job = models.ForeignKey(ForecastJob, on_delete=models.CASCADE, related_name="model_results", null=True)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES)
    file_path = models.CharField(max_length=500)
    params = models.JSONField(default=dict)
    mae = models.FloatField(null=True, blank=True)
    mape = models.FloatField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    mlflow_run_id = models.CharField(max_length=100, blank=True, default="")
    trained_at = models.DateTimeField(auto_now_add=True)
    is_best = models.BooleanField(default=False)
    is_comparable = models.BooleanField(default=True)

    class Meta:
        ordering = ["mae"]

    def __str__(self):
        best = " ★" if self.is_best else ""
        return f"{self.model_type}{best} for {self.product.name}"
