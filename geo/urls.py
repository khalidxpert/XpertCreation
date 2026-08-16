from django.urls import path

from . import views

app_name = "geo"

urlpatterns = [path("", views.where, name="where")]
