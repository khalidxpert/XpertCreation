from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta), path("nearby/", views.nearby), path("quote/", views.quote), path("rider/", views.rider),
    path("rides/", views.rides), path("rides/<int:pk>/", views.ride), path("rides/<int:pk>/<str:act>/", views.ride_act),
    path("track/<str:token>/", views.track),
    path("driver/", views.driver), path("driver/docs/", views.driver_docs), path("driver/docs/<int:doc>/", views.driver_doc_file),
    path("driver/submit/", views.driver_submit), path("driver/loc/", views.driver_loc), path("driver/feed/", views.driver_feed),
    path("team/", views.team), path("team/<str:kind>/<int:pk>/", views.team_act),
]
