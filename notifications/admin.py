from django.contrib import admin

from .models import ChatMessage, ChatThread, Notification

admin.site.register(Notification)
admin.site.register(ChatThread)
admin.site.register(ChatMessage)


from django.contrib import admin as _admin
from .models import ChatBlock as _ChatBlock, ChatReport as _ChatReport


@_admin.register(_ChatReport)
class ChatReportAdmin(_admin.ModelAdmin):
    list_display = ("thread", "reporter", "reason", "handled", "created_at")
    list_filter = ("handled", "reason")
    list_editable = ("handled",)


_admin.site.register(_ChatBlock)
