from django.urls import path

from . import views

urlpatterns = [
    path("contacts/", views.contacts, name="find-contacts"),
    path("settings/", views.find_settings, name="find-settings"),
]
