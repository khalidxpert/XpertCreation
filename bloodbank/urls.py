from django.urls import path

from . import views

app_name = "bloodbank"

urlpatterns = [
    path("me/", views.me, name="me"),
    path("search/", views.search, name="search"),
    path("cities/", views.cities, name="cities"),
    path("stats/", views.stats, name="stats"),

    path("requests/", views.requests_view, name="requests"),
    path("requests/<int:pk>/", views.request_detail, name="request-detail"),
    path("requests/<int:pk>/close/", views.close_request, name="close-request"),

    path("ask/", views.ask, name="ask"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/answer/", views.answer, name="answer"),
    path("directory/", views.directory, name="directory"),
    path("location/", views.location, name="location"),
    path("donated/", views.donated, name="donated"),
    path("requests/<int:pk>/match/", views.match, name="match"),

    path("report/", views.report, name="report"),
]
