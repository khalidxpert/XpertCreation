from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import EmailCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = [
        "email", "full_name", "phone", "is_email_verified",
        "requires_manual_review", "is_blocked", "daily_limit_pkr", "date_joined",
    ]
    list_filter = ["is_email_verified", "is_blocked", "requires_manual_review", "is_staff"]
    search_fields = ["email", "full_name", "phone", "signup_ip"]
    readonly_fields = ["date_joined", "last_login", "signup_ip", "last_login_ip"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone", "preferred_lang")}),
        ("Trust and limits", {
            "fields": ("is_email_verified", "daily_limit_pkr",
                       "requires_manual_review", "is_blocked", "block_reason"),
        }),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Trace", {"fields": ("signup_ip", "last_login_ip", "date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "full_name", "phone"),
        }),
    )


@admin.register(EmailCode)
class EmailCodeAdmin(admin.ModelAdmin):
    """Read only on purpose. Staff must never be able to read or mint a code."""
    list_display = ["user", "purpose", "created_at", "expires_at", "attempts", "used_at"]
    list_filter = ["purpose"]
    search_fields = ["user__email"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
