from django.urls import path

from . import views

urlpatterns = [
    path("search/", views.SearchView.as_view(), name="api-search"),
    path("jobs/<int:job_id>/", views.JobStatusView.as_view(), name="api-job-status"),
    path("products/<int:product_id>/", views.ProductDetailView.as_view(), name="api-product-detail"),
    path(
        "products/<int:product_id>/forecast/",
        views.ProductForecastView.as_view(),
        name="api-product-forecast",
    ),
    path(
        "products/<int:product_id>/retrain/",
        views.ProductRetrainView.as_view(),
        name="api-product-retrain",
    ),
]
