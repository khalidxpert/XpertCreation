from django.urls import path

from . import views

urlpatterns = [
    path("beat/", views.beat, name="rewards-beat"),
    path("board/", views.board, name="rewards-board"),
    path("me/", views.me, name="rewards-me"),
]
