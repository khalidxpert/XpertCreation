from django.urls import path

from . import views

urlpatterns = [path("", views.matches, name="predict"), path("<int:pk>/pick/", views.pick, name="predict-pick"), path("<int:pk>/result/", views.settle, name="predict-result")]
