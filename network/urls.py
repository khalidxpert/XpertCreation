from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.me, name="net-me"),
    path("me/skills/", views.skill_add, name="net-skill-add"),
    path("me/skills/<int:pk>/delete/", views.skill_delete, name="net-skill-delete"),
    path("me/experience/", views.exp_save, name="net-exp-save"),
    path("me/experience/<int:pk>/delete/", views.exp_delete, name="net-exp-delete"),
    path("me/education/", views.edu_save, name="net-edu-save"),
    path("me/education/<int:pk>/delete/", views.edu_delete, name="net-edu-delete"),
    path("me/requests/", views.requests_list, name="net-requests"),
    path("me/requests/<int:pk>/<str:action>/", views.request_respond, name="net-request-respond"),
    path("me/tick/", views.tick_apply, name="net-tick"),
    path("me/people/<str:which>/", views.my_people, name="net-my-people"),
    path("people/", views.people, name="net-people"),
    path("cities/", views.cities, name="net-cities"),
    path("in/<slug:slug>/", views.profile, name="net-profile"),
    path("in/<slug:slug>/endorse/", views.endorse, name="net-endorse"),
    path("in/<slug:slug>/report/", views.report, name="net-report"),
    path("in/<slug:slug>/connect/", views.connect, name="net-connect"),
    path("in/<slug:slug>/disconnect/", views.disconnect, name="net-disconnect"),
    path("in/<slug:slug>/message/", views.message, name="net-message"),
    path("in/<slug:slug>/follow/", views.follow, name="net-follow"),
]
