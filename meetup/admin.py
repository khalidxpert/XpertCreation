from django.contrib import admin
from .models import MeetGroup, Meetup, MeetRsvp, MeetReview


@admin.register(MeetGroup)
class MeetGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "category", "organizer", "members_count", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "city", "organizer__username")


@admin.register(Meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = ("title", "group", "city", "starts_at", "seats", "is_active", "cancelled")
    list_filter = ("is_active", "cancelled", "is_online")
    search_fields = ("title", "city", "group__name")


admin.site.register(MeetRsvp)
admin.site.register(MeetReview)
