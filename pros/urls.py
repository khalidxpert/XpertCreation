from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta), path("list/", views.plist), path("p/<int:pk>/", views.pro_page),
    path("me/", views.me), path("me/photo/", views.me_photo),
    path("jobs/", views.jobs), path("jobs/<int:pk>/", views.job), path("jobs/<int:pk>/photo/", views.job_photo),
    path("jobs/<int:pk>/<str:act>/", views.job_act),
    path("feed/", views.feed), path("offers/<int:pk>/", views.offer_act),
    path("report/", views.report), path("reviews/<int:pk>/reply/", views.review_reply),
    path("team/", views.team), path("team/<str:kind>/<int:pk>/<str:act>/", views.team_act), path("og/<int:pk>/", views.og),
]
