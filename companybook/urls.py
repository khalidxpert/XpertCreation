from django.urls import path

from . import views

urlpatterns = [path("", views.book), path("entries/", views.add), path("entries/<int:pk>/", views.delete), path("export.csv", views.export)]
