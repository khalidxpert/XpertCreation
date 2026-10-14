from django.urls import path

from . import views

urlpatterns = [
    path("contacts/", views.contacts, name="find-contacts"),
    path("settings/", views.find_settings, name="find-settings"),
    path("forget/", views.forget, name="find-forget"),
    path("suggest/", views.suggest, name="find-suggest"),
]
