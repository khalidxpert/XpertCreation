from django.urls import path

from . import views

app_name = "games"

urlpatterns = [
    path('rooms/live/', views.rooms_live, name='rooms-live'),
    path('rooms/create/', views.room_create, name='room-create'),
    path('rooms/join/', views.room_join, name='room-join'),
    path('rooms/<str:code>/', views.room_state, name='room-state'),
    path('rooms/<str:code>/move/', views.room_move, name='room-move'),
    path('rooms/<str:code>/leave/', views.room_leave, name='room-leave'),
    path("memory/start/", views.memory_start, name="memory-start"),
    path("memory/flip/", views.memory_flip, name="memory-flip"),
    path("tictac/start/", views.tictac_start, name="tictac-start"),
    path("tictac/move/", views.tictac_move, name="tictac-move"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("me/", views.my_stats, name="my-stats"),
]
