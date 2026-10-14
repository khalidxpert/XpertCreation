from django.urls import path

from . import views

urlpatterns = [
    path("saved/", views.saved_list),
    path("saved/status/", views.saved_status),
    path("saved/<int:pid>/", views.saved_toggle),
    path("repost/<int:pid>/", views.repost),
    path("embed/", views.embed),
    path("view/<int:uid>/", views.view),
    path("stats/", views.stats),
    path("privacy/", views.privacy),
    path("tags/trending/", views.trending),
    path("tags/mine/", views.my_tags),
    path("tags/<str:name>/", views.tag_status),
    path("tags/<str:name>/follow/", views.tag_follow),
    path("export/", views.export),
]
