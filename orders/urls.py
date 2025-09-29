from django.urls import path

from .views import Orders


app_name = "orders"

urlpatterns = [
    path("", Orders.as_view(), name="orders"),
]
