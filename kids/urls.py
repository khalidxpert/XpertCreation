from django.urls import path

from . import views

urlpatterns = [path("", views.videos, name="kids"), path("channels/", views.channels, name="kids-channels"),
               path("channels/<int:pk>/", views.channels, name="kids-channel"), path("hide/<str:vid>/", views.hide, name="kids-hide")]
