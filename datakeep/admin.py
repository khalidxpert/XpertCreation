from django.contrib import admin

from .models import KeptRecord


@admin.register(KeptRecord)
class KeptRecordAdmin(admin.ModelAdmin):
    list_display = ("kind", "no", "role", "amount", "fee", "status", "provider", "provider_ref", "paid_at", "deleted_at")
    list_filter = ("kind", "status")
    search_fields = ("no", "provider_ref")
