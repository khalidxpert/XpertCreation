from django.contrib import admin

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("slug", "owner", "active", "hidden", "views", "scans", "saves", "updated_at")
    list_filter = ("active", "hidden")
    list_editable = ("hidden",)
    search_fields = ("slug", "owner__email")
