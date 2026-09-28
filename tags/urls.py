from django.urls import path

from . import views

urlpatterns = [
    path("popular/", views.popular, name="tags-popular"),
    path("<str:name>/", views.tag_posts, name="tags-posts"),
]
