from django.urls import path

from . import views

urlpatterns = [path("token/", views.token, name="irc-token"), path("verify/", views.verify, name="irc-verify")]
