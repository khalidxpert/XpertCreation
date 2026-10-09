from django.urls import path

from . import views

urlpatterns = [
    path("view/", views.view, name="ads-view"),
    path("click/", views.click, name="ads-click"),
    path("stats/", views.stats, name="ads-stats"),
]
