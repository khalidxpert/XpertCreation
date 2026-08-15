from django.urls import path

from . import views

app_name = "typingtutor"

urlpatterns = [
    path("drills/", views.drills, name="drills"),
    path("start/", views.start, name="start"),
    path("finish/", views.finish, name="finish"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("me/", views.my_stats, name="my-stats"),
]
