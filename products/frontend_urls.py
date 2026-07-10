from django.urls import path

from . import frontend_views

urlpatterns = [
    path("", frontend_views.home, name="home"),
    path("product/<int:product_id>/", frontend_views.product_detail, name="product-detail"),
]
