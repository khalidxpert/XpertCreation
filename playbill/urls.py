from django.urls import path
from . import views

urlpatterns = [
    path("config/", views.config),
    path("order/", views.order),
    path("verify/", views.verify),
]
