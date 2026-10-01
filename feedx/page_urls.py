from django.urls import re_path

from . import views

urlpatterns = [re_path(r"^u/(?P<username>[A-Za-z0-9_]{3,20})/?$", views.by_username)]
