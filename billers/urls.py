from django.urls import path

from . import views

urlpatterns = [path("", views.billers, name="billers"), path("<int:pk>/", views.biller, name="biller")]
