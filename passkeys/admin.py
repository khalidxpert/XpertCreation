from django.contrib import admin

from .models import Passkey


@admin.register(Passkey)
class PasskeyAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "created_at", "last_used")
    search_fields = ("user__email", "name")
    exclude = ("public_key",)
