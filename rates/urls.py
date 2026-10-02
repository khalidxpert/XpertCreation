from django.urls import path

from . import views

urlpatterns = [path("", views.rates, name="rates"), path("set/", views.set_rates, name="rates-set")]
