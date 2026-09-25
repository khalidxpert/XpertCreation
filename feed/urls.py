from django.urls import path

from . import views

urlpatterns = [
    path("posts/", views.posts, name="feed-posts"),
    path("posts/<int:pk>/", views.post_detail, name="feed-post"),
    path("posts/<int:pk>/react/", views.react, name="feed-react"),
    path("posts/<int:pk>/comments/", views.comments, name="feed-comments"),
    path("posts/<int:pk>/report/", views.report, name="feed-report"),
    path("comments/<int:pk>/", views.comment_delete, name="feed-comment"),
]
