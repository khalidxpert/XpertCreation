from django.urls import path

from . import views, views2, views3

urlpatterns = [
    path("frames/", views.frames), path("frame/", views.frame),
    path("polls/", views.polls), path("polls/<int:pid>/vote/", views.vote),
    path("ambassadors/", views.ambassadors), path("ambassadors/apply/", views.amb_apply), path("ambassadors/team/<int:aid>/<str:act>/", views.amb_team),
    path("people/", views2.people), path("people/<str:act>/", views2.people_set), path("rel/", views2.rel),
    path("twostep/", views2.twostep), path("twostep/login/", views2.twostep_login), path("twostep/resend/", views2.twostep_resend),
    path("recs/", views3.recs), path("recs/<int:rid>/<str:act>/", views3.rec_act),
    path("featured/", views3.featured), path("featured/<int:fid>/remove/", views3.featured_remove),
    path("coreviews/", views3.coreviews), path("coreviews/<int:rid>/<str:act>/", views3.corev_act),
    path("events/", views3.events), path("events/<int:eid>/", views3.event), path("events/<int:eid>/<str:act>/", views3.event_act),
    path("articles/", views3.articles), path("articles/<int:aid>/", views3.article), path("articles/<int:aid>/<str:act>/", views3.article_act),
    path("subscribe/", views3.subscribe),
    path("memories/", views.memories), path("celebrate/", views.celebrate), path("wish/", views.wish),
]
