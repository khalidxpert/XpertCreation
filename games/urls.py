from django.urls import path

from . import views

app_name = "games"

urlpatterns = [
    path("memory/start/", views.memory_start, name="memory-start"),
    path("memory/flip/", views.memory_flip, name="memory-flip"),
    path("tictac/start/", views.tictac_start, name="tictac-start"),
    path("tictac/move/", views.tictac_move, name="tictac-move"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("me/", views.my_stats, name="my-stats"),
]
