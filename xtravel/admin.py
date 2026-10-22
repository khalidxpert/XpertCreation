from django.contrib import admin

from .models import Booking, Property, Tour


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "company", "status", "featured", "created_at"]
    list_filter = ["status", "kind", "city"]


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ["title", "destination", "company", "price", "status", "featured"]
    list_filter = ["status"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["code", "kind", "name", "start", "end", "qty", "total", "status", "created_at"]
    list_filter = ["status", "kind"]
