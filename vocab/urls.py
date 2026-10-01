from django.urls import path

from . import views

urlpatterns = [path("me/", views.me, name="vocab-me"), path("answer/", views.answer, name="vocab-answer")]
