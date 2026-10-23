from django.contrib import admin

from .models import Job, Track


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "status", "lang", "duration", "minutes", "created_at", "video_gone")
    list_filter = ("status",)
    exclude = ("segments",)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "lang", "status", "progress")
    exclude = ("segments",)
