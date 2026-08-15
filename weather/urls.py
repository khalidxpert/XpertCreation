from django.urls import path

from . import views

app_name = "weather"

urlpatterns = [
    path("", views.weather, name="weather"),
    path("cities/", views.cities, name="cities"),
]
