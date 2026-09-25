from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("mine/", views.my_notifications, name="mine"),
    path("read/", views.mark_read, name="read"),
    path("clear/", views.clear_all, name="clear"),
    path("threads/", views.my_threads, name="threads"),
    path("threads/start/", views.start_thread, name="start"),
    path("threads/<int:pk>/", views.thread_detail, name="thread"),
]
