from django.contrib import admin

from .models import Score, Session, Stats


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ["user", "game", "level", "points", "seconds", "won", "created_at"]
    list_filter = ["game", "level", "won"]
    search_fields = ["user__email"]
    readonly_fields = [f.name for f in Score._meta.fields]

    def has_add_permission(self, request):
        # A hand-made score would sit on the leaderboard looking real.
        return False


@admin.register(Stats)
class StatsAdmin(admin.ModelAdmin):
    list_display = ["user", "played", "won", "best_memory", "best_tictac",
                    "current_streak", "longest_streak"]
    search_fields = ["user__email"]


admin.site.register(Session)
