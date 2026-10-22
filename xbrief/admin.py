from django.contrib import admin

from .models import Doc


@admin.register(Doc)
class DocAdmin(admin.ModelAdmin):
    """Only the facts needed for support - the file itself is never opened from admin."""
    list_display = ["id", "owner", "folder", "mime", "size", "expires", "created_at"]
    list_filter = ["folder"]
    readonly_fields = [f.name for f in Doc._meta.fields]

    def has_add_permission(self, request):
        return False
