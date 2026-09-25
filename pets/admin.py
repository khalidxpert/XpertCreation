from django.contrib import admin

from .models import FoundNote, HealthRecord, LostFound, Pet, VaccineTemplate


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "owner", "tag_code", "is_lost", "created_at")
    list_filter = ("species", "is_lost")
    search_fields = ("name", "tag_code", "owner__email")


@admin.register(LostFound)
class LostFoundAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "city", "status", "reporter", "created_at")
    list_filter = ("kind", "status", "species")
    search_fields = ("title", "city", "description")


@admin.register(VaccineTemplate)
class VaccineTemplateAdmin(admin.ModelAdmin):
    list_display = ("species", "vaccine_name", "due_at_weeks", "repeat_every_days")
    list_filter = ("species",)


admin.site.register(HealthRecord)
admin.site.register(FoundNote)
