from django.contrib import admin
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.views import APIView


class APIRootView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({
            "name": "Price Forecast API",
            "endpoints": {
                "search": "/api/search/",
                "jobs": "/api/jobs/<id>/",
                "forecast": "/api/products/<id>/forecast/",
                "retrain": "/api/products/<id>/retrain/",
                "admin": "/admin/",
            },
        })


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("products.urls")),
    path("", APIRootView.as_view(), name="api-root"),
]
