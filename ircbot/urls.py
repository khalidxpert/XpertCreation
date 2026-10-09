from django.urls import path

from . import views

urlpatterns = [path("post/", views.post, name="ircbot-post"), path("feed/", views.feed, name="ircbot-feed"),
               path("claim/", __import__("rewards.views", fromlist=["irc_claim"]).irc_claim, name="ircbot-claim")]
