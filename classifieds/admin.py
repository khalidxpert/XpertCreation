from django.contrib import admin

from .models import Ad, AdImage, Category, Favorite, Report


class AdImageInline(admin.TabularInline):
    model = AdImage
    extra = 1


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "city", "status", "views", "created_at")
    list_filter = ("status", "condition", "price_type", "category")
    search_fields = ("title", "description", "city")
    inlines = [AdImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "ad", "created_at")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("ad", "user", "reason", "created_at")
