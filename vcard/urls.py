from django.urls import path

from . import views

app_name = "vcard"

urlpatterns = [
    path("mine/", views.my_card, name="mine"),
    path("c/<str:token>/", views.public_card, name="public"),
]
