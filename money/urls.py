from django.urls import path

from . import views

urlpatterns = [path("", views.book, name="money-book"), path("files/", views.file_add, name="money-file-add"),
               path("files/<str:fid>/", views.file_one, name="money-file")]
