from django.urls import path

from . import views

urlpatterns = [
    path("rooms/", views.create), path("rooms/<str:code>/", views.room), path("rooms/<str:code>/join/", views.join),
    path("rooms/<str:code>/leave/", views.leave), path("rooms/<str:code>/start/", views.start),
    path("rooms/<str:code>/shot/", views.shot), path("rooms/<str:code>/skip/", views.skip),
]
