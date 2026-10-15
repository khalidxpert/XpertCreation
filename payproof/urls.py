from django.urls import path

from . import views

urlpatterns = [
    path("info/", views.info),
    path("mine/", views.mine),
    path("orders/<int:oid>/", views.send),
    path("pay/<str:kind>/<str:ref>/", views.send_any),
    path("team/", views.team),
    path("team/account/", views.team_account),
    path("team/<int:pid>/<str:act>/", views.team_act),
    path("file/<int:pid>/", views.file),
]
