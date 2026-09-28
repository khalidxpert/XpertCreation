from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(r"^tag/(?P<name>[A-Za-z][A-Za-z0-9_]{1,49})/?$", views.page),
    path("sitemap-tags.xml", views.sitemap),
]
