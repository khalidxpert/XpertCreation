from django.urls import path
from . import views

urlpatterns = [
    path("config/", views.config),
    path("mine/", views.mine),
    path("groups/", views.groups),                                  # GET list, POST create
    path("groups/<int:gid>/join/", views.group_join),
    path("groups/<int:gid>/leave/", views.group_leave),
    path("groups/<int:gid>/edit/", views.group_edit),
    path("groups/<int:gid>/members/", views.group_members),
    path("groups/<int:gid>/meetups/", views.meetup_create),
    path("meetups/", views.meetups),
    path("meetups/<int:mid>/rsvp/", views.rsvp),
    path("meetups/<int:mid>/cancel/", views.meetup_cancel),
    path("meetups/<int:mid>/review/", views.review),
    path("groups/<slug:slug>/", views.group_detail),
    path("meetups/<slug:slug>/", views.meetup_detail),
]
