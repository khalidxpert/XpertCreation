from django.contrib import admin
from .models import GroupRole


@admin.register(GroupRole)
class GroupRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "color", "icon", "position", "hoist")
    search_fields = ("name", "group__name")
