from django.contrib import admin

from .models import ForecastJob, PricePoint, Product, ProductModel


class PricePointInline(admin.TabularInline):
    model = PricePoint
    extra = 0
    readonly_fields = ("recorded_at", "price", "scraped_at")


class ProductModelInline(admin.TabularInline):
    model = ProductModel
    extra = 0
    readonly_fields = ("model_type", "mae", "mape", "rmse", "is_best", "trained_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "external_id", "last_scraped_at", "created_at")
    search_fields = ("name", "external_id")
    inlines = [PricePointInline, ProductModelInline]


@admin.register(ForecastJob)
class ForecastJobAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "status", "created_at", "completed_at")
    list_filter = ("status",)
    readonly_fields = ("celery_task_id", "error_message", "created_at", "completed_at")


@admin.register(ProductModel)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ("product", "model_type", "mae", "mape", "rmse", "is_best", "trained_at")
    list_filter = ("model_type", "is_best", "is_comparable")
