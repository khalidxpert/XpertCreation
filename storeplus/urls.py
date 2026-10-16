from django.urls import path

from . import views

urlpatterns = [
    path("countries/", views.countries), path("me/", views.me), path("shop/<slug:slug>/", views.shop), path("vcf/<slug:slug>/", views.vcf),
    path("drop/offers/", views.drop_offers), path("drop/catalog/", views.drop_catalog), path("drop/add/", views.drop_add), path("drop/mine/", views.drop_mine),
]
