from django.contrib import admin

from .models import Birthday, Sent


@admin.register(Birthday)
class BirthdayAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "pretty", "relation", "days_before", "created_at"]
    list_filter = ["month", "relation"]
    search_fields = ["name", "owner__email"]
    readonly_fields = ["created_at", "last_advance_year", "last_dayof_year"]


@admin.register(Sent)
class SentAdmin(admin.ModelAdmin):
    """Read only: this is the record that answers "why did I get two emails"."""
    list_display = ["birthday", "kind", "for_year", "ok", "sent_at"]
    list_filter = ["kind", "ok"]
    readonly_fields = [f.name for f in Sent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
