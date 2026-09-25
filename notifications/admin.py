from django.contrib import admin

from .models import ChatMessage, ChatThread, Notification

admin.site.register(Notification)
admin.site.register(ChatThread)
admin.site.register(ChatMessage)
