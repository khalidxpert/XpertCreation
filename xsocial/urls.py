from django.urls import path

from . import views

urlpatterns = [
    path("frames/", views.frames), path("frame/", views.frame),
    path("polls/", views.polls), path("polls/<int:pid>/vote/", views.vote),
    path("ambassadors/", views.ambassadors), path("ambassadors/apply/", views.amb_apply), path("ambassadors/team/<int:aid>/<str:act>/", views.amb_team),
    path("memories/", views.memories), path("celebrate/", views.celebrate), path("wish/", views.wish),
]
