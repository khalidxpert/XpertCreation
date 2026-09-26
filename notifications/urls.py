from django.urls import path

from . import broadcast, chatx, groups, push, views

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
    path("groups/", groups.groups, name="groups"),
    path("groups/invites/", groups.invites, name="group-invites"),
    path("groups/invites/<int:pk>/<str:action>/", groups.invite_answer, name="group-invite-answer"),
    path("groups/privacy/", groups.privacy, name="group-privacy"),
    path("groups/join/<str:code>/", groups.group_join, name="group-join"),
    path("groups/files/<int:pk>/", groups.group_file, name="group-file"),
    path("groups/<int:pk>/", groups.group_detail, name="group"),
    path("groups/<int:pk>/typing/", groups.group_typing, name="group-typing"),
    path("groups/<int:pk>/settings/", groups.group_settings, name="group-settings"),
    path("groups/<int:pk>/members/", groups.group_members, name="group-members"),
    path("groups/<int:pk>/members/<int:uid>/", groups.group_member, name="group-member"),
    path("groups/<int:pk>/leave/", groups.group_leave, name="group-leave"),
    path("groups/<int:pk>/mute/", groups.group_mute, name="group-mute"),
    path("groups/<int:pk>/report/", groups.group_report, name="group-report"),
    path("groups/<int:pk>/link/", groups.group_link, name="group-link"),
    path("threads/", views.my_threads, name="threads"),
    path("threads/start/", views.start_thread, name="start"),
    path("threads/unread/", views.unread_count, name="unread"),
    path("threads/delete/", views.threads_delete, name="delete-threads"),
    path("threads/<int:pk>/", views.thread_detail, name="thread"),
    path("threads/<int:pk>/typing/", views.thread_typing, name="typing"),
    path("threads/<int:pk>/media/", chatx.thread_media, name="media"),
    path("threads/<int:pk>/export/", chatx.thread_export, name="export"),
    path("files/<int:pk>/", chatx.file_download, name="file"),
    path("threads/<int:pk>/block/", views.thread_block, name="block"),
    path("threads/<int:pk>/report/", views.thread_report, name="report"),
    path("threads/<int:pk>/clear/", views.thread_clear, name="clear-thread"),
    path("threads/<int:pk>/disappear/", views.thread_disappear, name="disappear"),
]
