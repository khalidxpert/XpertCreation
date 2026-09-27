from django.urls import path

from . import views

urlpatterns = [
    path("slug/", views.slug_check, name="cards-slug"),
    path("mine/", views.mine, name="cards-mine"),
    path("<int:pk>/", views.card, name="cards-card"),
    path("<int:pk>/image/", views.image, name="cards-image"),
    path("public/<slug:slug>/", views.public, name="cards-public"),
    path("public/<slug:slug>/click/", views.click, name="cards-click"),
    path("public/<slug:slug>/report/", views.report, name="cards-report"),
]
