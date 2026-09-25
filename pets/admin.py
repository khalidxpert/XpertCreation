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


from .models import AdoptionPost, AdoptionRequest, VetClinic


@admin.register(AdoptionPost)
class AdoptionPostAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "city", "status", "owner", "hidden", "created_at")
    list_filter = ("status", "species", "hidden")
    list_editable = ("hidden",)
    search_fields = ("name", "city", "description")


@admin.register(VetClinic)
class VetClinicAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "phone", "emergency", "approved", "created_at")
    list_filter = ("approved", "emergency")
    list_editable = ("approved",)
    search_fields = ("name", "city", "address")


admin.site.register(AdoptionRequest)
