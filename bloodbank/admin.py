from django.contrib import admin

from .models import Ask, Donor, Report, Request


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ["name", "blood_group", "city", "is_available", "is_eligible",
                    "is_verified", "is_blocked", "updated_at"]
    list_filter = ["blood_group", "city", "is_available", "is_verified",
                   "is_blocked", "share_location"]
    search_fields = ["name", "city", "user__email"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(boolean=True, description="Eligible")
    def is_eligible(self, obj):
        return obj.is_eligible


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ["blood_group", "city", "hospital", "urgency", "status",
                    "created_at", "expires_at"]
    list_filter = ["status", "urgency", "blood_group", "city"]
    search_fields = ["hospital", "city", "requester__email"]


@admin.register(Ask)
class AskAdmin(admin.ModelAdmin):
    """Read only. This is the record of who was given which number and when -
    the only thing that makes a harassment complaint answerable."""
    list_display = ["id", "request", "donor", "status", "created_at", "answered_at"]
    list_filter = ["status"]
    search_fields = ["donor__name", "request__hospital"]
    readonly_fields = [f.name for f in Ask._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "reporter", "ask", "handled", "created_at"]
    list_filter = ["handled"]
    search_fields = ["reporter__email", "reason"]
