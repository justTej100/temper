from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def product_detail(request, product_id):
    return render(request, "product.html", {"product_id": product_id})
