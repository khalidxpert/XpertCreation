from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(r"^job/(?P<pk>\d+)/?$", views.job),
    re_path(r"^post/(?P<pk>\d+)/?$", views.post),
    re_path(r"^adopt/(?P<pk>\d+)/?$", views.adopt),
    re_path(r"^in/(?P<slug>[a-z0-9_-]+)/?$", views.profile),
    re_path(r"^show/(?P<kind>tv|movie)-(?P<pk>\d+)/?$", views.show),
    path("sitemap-dynamic.xml", views.sitemap),
]
