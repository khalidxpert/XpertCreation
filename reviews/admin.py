from django.contrib import admin
from django.utils import timezone

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["module", "stars", "short", "user", "state", "created_at"]
    list_filter = ["state", "module", "stars"]
    search_fields = ["comment", "user__email"]
    readonly_fields = ["created_at", "updated_at", "user", "module", "stars"]
    actions = ["publish", "reject"]

    @admin.display(description="Comment")
    def short(self, obj):
        return (obj.comment[:70] + "\u2026") if len(obj.comment) > 70 else (obj.comment or "\u2014")

    @admin.action(description="Publish the comment")
    def publish(self, request, queryset):
        n = queryset.update(state=Review.PUBLISHED, reviewed_at=timezone.now())
        self.message_user(request, "%d published." % n)

    @admin.action(description="Reject the comment (the stars still count)")
    def reject(self, request, queryset):
        n = queryset.update(state=Review.REJECTED, reviewed_at=timezone.now())
        self.message_user(request, "%d rejected." % n)

    def get_queryset(self, request):
        # Waiting ones first: that is what this page is for.
        return super().get_queryset(request).order_by(
            "state", "-created_at").select_related("user")
