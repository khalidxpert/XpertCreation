from django.contrib import admin

from .models import ModApplication, Ticket, TicketMessage


@admin.register(ModApplication)
class ModApplicationAdmin(admin.ModelAdmin):
    list_display = ["user", "state", "created_at", "decided_by"]
    list_filter = ["state"]
    search_fields = ["user__email", "why"]


class MessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ["author", "is_staff", "body", "created_at"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "user", "priority", "state", "updated_at"]
    list_filter = ["state", "priority"]
    search_fields = ["subject", "user__email"]
    inlines = [MessageInline]
