from django.contrib import admin

from .models import LegalDocumentRequest


@admin.register(LegalDocumentRequest)
class LegalDocumentRequestAdmin(admin.ModelAdmin):
    list_display = ("reference_no", "doc_type", "user", "created_at")
    list_filter = ("doc_type", "created_at")
    search_fields = ("reference_no", "user__username")
    readonly_fields = ("reference_no", "payload", "created_at")
    date_hierarchy = "created_at"
