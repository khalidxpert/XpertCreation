from django.urls import path
from . import views

urlpatterns = [
    path("ice/", views.ice),
    path("start/", views.start),
    path("incoming/", views.incoming),
    path("active/", views.active),
    path("meet/new/", views.meet_new),
    path("meet/mine/", views.meet_mine),
    path("meet/<str:code>/", views.meet_find),
    path("<int:pk>/", views.detail),
    path("<int:pk>/join/", views.join),
    path("<int:pk>/decline/", views.decline),
    path("<int:pk>/leave/", views.leave),
    path("<int:pk>/poll/", views.poll),
    path("<int:pk>/signal/", views.signal),
]
