from django.contrib import admin
from .models import LessonQA


@admin.register(LessonQA)
class LessonQAAdmin(admin.ModelAdmin):
    list_display = ("course", "lesson", "user", "short", "parent", "helpful", "hidden", "created")
    list_filter = ("course", "hidden", "helpful")
    search_fields = ("body", "user__username")

    def short(self, o):
        return o.body[:60]
