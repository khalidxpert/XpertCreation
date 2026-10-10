from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta), path("listings/", views.listings), path("listings/<int:pk>/", views.listing),
    path("listings/<int:pk>/image/", views.image), path("listings/<int:pk>/<str:act>/", views.act),
]
