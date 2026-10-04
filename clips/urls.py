from django.urls import path

from . import views

urlpatterns = [path("", views.feed, name="clips"), path("upload/", views.upload, name="clips-upload"), path("mine/", views.mine, name="clips-mine"),
               path("review/", views.review, name="clips-review"), path("<int:pk>/", views.clip, name="clip"), path("<int:pk>/<str:what>/", views.act, name="clip-act")]
