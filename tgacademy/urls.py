from django.urls import path

from . import pay_views, views

urlpatterns = [
    path("provision", views.provision),
    path("link", views.link),
    path("go/<str:token>", views.go),
    path("access/", pay_views.access),
    path("buy/<slug:slug>/", pay_views.buy),
    path("redeem/", pay_views.redeem),
    path("ask/", pay_views.ask),
    path("team/", pay_views.team),
    path("team/coupon/", pay_views.team_coupon),
    path("team/coupon/<int:pk>/off/", pay_views.team_coupon_off),
    path("team/ask/<int:pk>/<str:act>/", pay_views.team_ask),
    path("team/paywall/", pay_views.team_paywall),
]
