from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home, name="sports-home"),
    path("cricket/", views.cricket, name="sports-cricket"),
    path("cricket/<str:mid>/", views.cricket_match, name="sports-cricket-match"),
    path("football/", views.football, name="sports-football"),
    path("football/table/<str:code>/", views.football_table, name="sports-football-table"),
    path("football/<int:mid>/", views.football_match, name="sports-football-match"),
    path("other/<str:kind>/", views.other, name="sports-other"),
    path("predict/", views.predict, name="sports-predict"),
]
