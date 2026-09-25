from django.contrib import admin

from .models import DonationItem, DonationPhoto, DonationReport, DonationRequest


class PhotoInline(admin.TabularInline):
    model = DonationPhoto
    extra = 0


@admin.register(DonationItem)
class DonationItemAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "donor", "city", "state", "created_at"]
    list_filter = ["category", "state", "condition"]
    search_fields = ["title", "donor__email", "city"]
    inlines = [PhotoInline]


@admin.register(DonationReport)
class DonationReportAdmin(admin.ModelAdmin):
    list_display = ["item", "reporter", "reason", "handled", "created_at"]
    list_filter = ["handled"]
    actions = ["mark_handled"]

    @admin.action(description="Mark as handled")
    def mark_handled(self, request, queryset):
        queryset.update(handled=True)


admin.site.register(DonationRequest)
