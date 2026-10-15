from django.urls import path

from . import views, views2

urlpatterns = [
    path("frames/", views.frames), path("frame/", views.frame),
    path("polls/", views.polls), path("polls/<int:pid>/vote/", views.vote),
    path("ambassadors/", views.ambassadors), path("ambassadors/apply/", views.amb_apply), path("ambassadors/team/<int:aid>/<str:act>/", views.amb_team),
    path("people/", views2.people), path("people/<str:act>/", views2.people_set), path("rel/", views2.rel),
    path("twostep/", views2.twostep), path("twostep/login/", views2.twostep_login), path("twostep/resend/", views2.twostep_resend),
    path("memories/", views.memories), path("celebrate/", views.celebrate), path("wish/", views.wish),
]
