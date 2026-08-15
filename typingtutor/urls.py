from django.urls import path

from . import views

app_name = "typingtutor"

urlpatterns = [
    path("drills/", views.drills, name="drills"),
    path("start/", views.start, name="start"),
    path("resume/", views.resume, name="resume"),
    path("abandon/", views.abandon, name="abandon"),
    path("progress/", views.progress, name="progress"),
    path("finish/", views.finish, name="finish"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("me/", views.my_stats, name="my-stats"),
]
