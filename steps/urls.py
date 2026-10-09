from django.urls import path

from . import views

urlpatterns = [
    path("walks/", views.walks), path("walks/<int:wid>/", views.walk), path("prefs/", views.prefs),
]
