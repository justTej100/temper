from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from forecasting.data_sources.base import get_data_source
from forecasting.trainer import predict_with_model

from .models import ForecastJob, Product, ProductModel
from .serializers import (
    ForecastJobSerializer,
    ProductModelSerializer,
    ProductSerializer,
    SearchRequestSerializer,
)
from .services import get_cached_best_model
from .tasks import run_forecast_pipeline


class SearchView(APIView):
    """Search for products and trigger forecasting if needed."""

    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]
        force_refresh = serializer.validated_data["force_refresh"]

        source = get_data_source()
        results = source.search(query)

        if not results:
            return Response({"results": [], "message": "No products found"})

        response_results = []
        for item in results:
            product, _ = Product.objects.get_or_create(
                external_id=item["external_id"],
                defaults={"name": item["name"], "source_url": item.get("source_url", "")},
            )
            if product.name != item["name"]:
                product.name = item["name"]
                product.save(update_fields=["name"])

            cached = None if force_refresh else get_cached_best_model(product)
            if cached:
                response_results.append({
                    "product_id": product.id,
                    "name": product.name,
                    "status": "ready",
                    "job_id": None,
                })
            else:
                job = ForecastJob.objects.create(
                    product=product,
                    status=ForecastJob.Status.PENDING,
                )
                run_forecast_pipeline.delay(job.id)
                response_results.append({
                    "product_id": product.id,
                    "name": product.name,
                    "status": "processing",
                    "job_id": job.id,
                })

        return Response({"query": query, "results": response_results})


class JobStatusView(APIView):
    """Poll the status of a forecast job."""

    def get(self, request, job_id):
        job = get_object_or_404(ForecastJob, id=job_id)
        return Response(ForecastJobSerializer(job).data)


class ProductDetailView(APIView):
    """Get product details with price history and model comparison."""

    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        return Response(ProductSerializer(product).data)


class ProductForecastView(APIView):
    """Get forecast results for a product."""

    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        best_model = (
            ProductModel.objects.filter(product=product, is_best=True)
            .order_by("-trained_at")
            .first()
            or ProductModel.objects.filter(product=product, is_comparable=True)
            .order_by("mae", "-trained_at")
            .first()
        )

        if not best_model:
            return Response(
                {"error": "No trained model available"},
                status=status.HTTP_404_NOT_FOUND,
            )

        price_points = product.price_points.all()
        forecast = predict_with_model(best_model, price_points)

        history = [
            {"date": pp.recorded_at.isoformat(), "price": float(pp.price)}
            for pp in price_points.order_by("recorded_at")
        ]

        latest_job = (
            ForecastJob.objects.filter(product=product, status=ForecastJob.Status.COMPLETE)
            .order_by("-completed_at")
            .first()
        )
        if latest_job:
            comparison_qs = ProductModel.objects.filter(
                job=latest_job, is_comparable=True
            ).order_by("mae")
        else:
            comparison_qs = ProductModel.objects.filter(
                product=product, is_comparable=True
            ).order_by("-trained_at")
            seen_types = set()
            latest_models = []
            for m in comparison_qs:
                if m.model_type not in seen_types:
                    seen_types.add(m.model_type)
                    latest_models.append(m)
            comparison_qs = latest_models

        comparison = ProductModelSerializer(comparison_qs, many=True).data

        return Response({
            "product_id": product.id,
            "product_name": product.name,
            "price_history": history,
            "forecast": forecast,
            "model_comparison": comparison,
            "best_model": best_model.model_type,
        })


class ProductRetrainView(APIView):
    """Force retrain models for a product."""

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        job = ForecastJob.objects.create(product=product, status=ForecastJob.Status.PENDING)
        run_forecast_pipeline.delay(job.id)
        return Response(
            {"job_id": job.id, "status": "processing"},
            status=status.HTTP_202_ACCEPTED,
        )
