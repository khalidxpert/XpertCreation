from django.urls import path

from . import views

app_name = "botlink"

urlpatterns = [
    path("mine/", views.my_links, name="mine"),
    path("code/", views.make_code, name="code"),
    path("unlink/", views.unlink, name="unlink"),
    path("bot/verify/", views.bot_verify, name="bot-verify"),
]
