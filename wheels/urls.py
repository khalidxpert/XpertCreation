from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta), path("ads/", views.ads), path("ads/<int:pk>/", views.ad), path("ads/<int:pk>/image/", views.ad_image),
    path("ads/<int:pk>/phone/", views.phone), path("ads/<int:pk>/offer/", views.offer), path("ads/<int:pk>/report/", views.report),
    path("ads/<int:pk>/<str:act>/", views.ad_act), path("mine/", views.mine), path("offers/<int:pk>/reply/", views.offer_reply),
    path("team/", views.team), path("team/<int:pk>/<str:act>/", views.team_act), path("og/<int:pk>/", views.og),
]
