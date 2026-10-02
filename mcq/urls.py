from django.urls import path

from . import views

urlpatterns = [path("today/", views.today, name="mcq-today"), path("practice/", views.practice, name="mcq-practice"), path("board/", views.board, name="mcq-board")]
