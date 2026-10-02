from django.urls import path

from . import views

urlpatterns = [
    path("", views.stories, name="stories"),
    path("<int:pk>/", views.one, name="story"),
    path("<int:pk>/seen/", views.seen, name="story-seen"),
]
