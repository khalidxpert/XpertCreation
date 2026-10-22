from django.contrib import admin

from .models import Live


@admin.register(Live)
class LiveAdmin(admin.ModelAdmin):
    list_display = ["id", "host", "title", "status", "started_at", "peak", "hearts"]
    list_filter = ["status"]
