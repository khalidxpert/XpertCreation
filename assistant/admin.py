from django.contrib import admin

from .models import AssistantUse


@admin.register(AssistantUse)
class AssistantUseAdmin(admin.ModelAdmin):
    list_display = ("day", "user", "count")
    list_filter = ("day",)
