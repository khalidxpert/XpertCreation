from django.urls import path

from . import views

urlpatterns = [
    path("", views.directory, name="gd-directory"),
    path("creators/", views.creators, name="gd-creators"),
    path("mine/", views.mine, name="gd-mine"),
]
