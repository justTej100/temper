from rest_framework import serializers

from .models import ForecastJob, PricePoint, Product, ProductModel


class PricePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricePoint
        fields = ("price", "recorded_at")


class ProductModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductModel
        fields = (
            "model_type",
            "params",
            "mae",
            "mape",
            "rmse",
            "is_best",
            "is_comparable",
            "trained_at",
        )


class ProductSerializer(serializers.ModelSerializer):
    price_points = PricePointSerializer(many=True, read_only=True)
    models = ProductModelSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "source_url",
            "external_id",
            "last_scraped_at",
            "price_points",
            "models",
        )


class ForecastJobSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ForecastJob
        fields = (
            "id",
            "product",
            "product_name",
            "status",
            "error_message",
            "created_at",
            "completed_at",
        )


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=255)
    force_refresh = serializers.BooleanField(default=False)
