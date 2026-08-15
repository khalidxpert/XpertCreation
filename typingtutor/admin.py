from django.contrib import admin

from .models import Drill, Score, Session, Stats


@admin.register(Drill)
class DrillAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "level", "lang", "length", "is_active", "order"]
    list_filter = ["kind", "lang", "is_active"]
    list_editable = ["order", "is_active"]
    search_fields = ["title", "content"]

    @admin.display(description="Characters")
    def length(self, obj):
        return len(obj.content)


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ["user", "mode", "wpm", "accuracy", "seconds", "created_at"]
    list_filter = ["mode"]
    search_fields = ["user__email"]
    readonly_fields = [f.name for f in Score._meta.fields]

    def has_add_permission(self, request):
        # Scores are earned. A hand-made row would sit on the leaderboard
        # looking exactly like a real one.
        return False


@admin.register(Stats)
class StatsAdmin(admin.ModelAdmin):
    list_display = ["user", "best_wpm", "best_accuracy", "total_runs",
                    "current_streak", "longest_streak", "last_day"]
    search_fields = ["user__email"]


admin.site.register(Session)
