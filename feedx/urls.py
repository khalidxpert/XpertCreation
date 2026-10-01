from django.urls import path

from . import views

urlpatterns = [
    path("people/", views.people, name="feedx-people"),
    path("meta/", views.meta, name="feedx-meta"),
    path("feelings/", views.feelings, name="feedx-feelings"),
    path("posts/<int:pk>/meta/", views.set_meta, name="feedx-set-meta"),
    path("posts/<int:pk>/reactions/", views.post_reactors, name="feedx-post-reactors"),
    path("comments/counts/", views.comment_counts, name="feedx-comment-counts"),
    path("comments/<int:pk>/react/", views.comment_react, name="feedx-comment-react"),
    path("comments/<int:pk>/reactions/", views.comment_reactors, name="feedx-comment-reactors"),
]
