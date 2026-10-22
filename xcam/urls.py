from django.urls import path
from . import views

urlpatterns = [path("clip/<str:kind>/<int:pk>/", views.clip)]
