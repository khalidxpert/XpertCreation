from django.urls import path

from . import views

urlpatterns = [
    path("chat/", views.chat, name="assistant-chat"),
    path("status/", views.status, name="assistant-status"),
    path("usage/", views.usage, name="assistant-usage"),
]
