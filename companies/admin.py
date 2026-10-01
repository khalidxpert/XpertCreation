from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "domain", "domain_verified_at", "hidden", "updated_at")
    list_filter = ("status", "hidden")
    search_fields = ("name", "owner__email", "domain")
    exclude = ("domain_token",)
