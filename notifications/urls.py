from django.urls import path

from . import broadcast, push, views

app_name = "notifications"

urlpatterns = [
    path("mine/", views.my_notifications, name="mine"),
    path("broadcast/", broadcast.broadcast, name="broadcast"),
    path("read/", views.mark_read, name="read"),
    path("clear/", views.clear_all, name="clear"),
    path("push/key/", push.public_key, name="push-key"),
    path("push/subscribe/", push.subscribe, name="push-subscribe"),
    path("push/unsubscribe/", push.unsubscribe, name="push-unsubscribe"),
    path("push/test/", push.test, name="push-test"),
    path("threads/", views.my_threads, name="threads"),
    path("threads/start/", views.start_thread, name="start"),
    path("threads/unread/", views.unread_count, name="unread"),
    path("threads/delete/", views.threads_delete, name="delete-threads"),
    path("threads/<int:pk>/", views.thread_detail, name="thread"),
    path("threads/<int:pk>/typing/", views.thread_typing, name="typing"),
    path("threads/<int:pk>/block/", views.thread_block, name="block"),
    path("threads/<int:pk>/report/", views.thread_report, name="report"),
    path("threads/<int:pk>/clear/", views.thread_clear, name="clear-thread"),
    path("threads/<int:pk>/disappear/", views.thread_disappear, name="disappear"),
]
