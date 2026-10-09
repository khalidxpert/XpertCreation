from django.urls import path

from . import views

urlpatterns = [path("wall/", views.wall, name="share-wall")]
