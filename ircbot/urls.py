from django.urls import path

from . import views

urlpatterns = [path("post/", views.post, name="ircbot-post"), path("feed/", views.feed, name="ircbot-feed")]
