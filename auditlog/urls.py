from django.urls import path

from . import views

urlpatterns = [
    path("events/", views.events, name="audit-events"),
    path("summary/", views.summary, name="audit-summary"),
    path("users/", views.users, name="audit-users"),
    path("export.csv", views.export, name="audit-export"),
]
