from django.urls import path

from . import views

urlpatterns = [
    path("shop/<slug:slug>/", views.shop_info), path("thread/", views.thread), path("mine/", views.mine),
    path("inbox/", views.inbox), path("inbox/<int:pk>/", views.inbox_thread), path("faqs/", views.faqs), path("unread/", views.unread), path("directory/", views.directory),
]
