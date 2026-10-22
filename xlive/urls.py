from django.urls import path

from . import views

urlpatterns = [
    path("", views.lives, name="live-list"),
    path("start/", views.start, name="live-start"),
    path("<int:pk>/", views.watch, name="live-watch"),
    path("<int:pk>/beat/", views.beat, name="live-beat"),
    path("<int:pk>/end/", views.end, name="live-end"),
    path("<int:pk>/stage/", views.stage, name="live-stage"),
    path("<int:pk>/block/", views.block, name="live-block"),
]
