from django.contrib import admin
from .models import PlayPurchase


@admin.register(PlayPurchase)
class PlayPurchaseAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "sku", "state", "gp_order", "order")
    list_filter = ("state", "sku")
    search_fields = ("gp_order", "user__username", "user__email")
    readonly_fields = ("token",)
