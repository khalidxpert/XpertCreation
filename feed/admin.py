from django.contrib import admin

from .models import Comment, Post, PostReport


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "short", "visibility", "reactions_count", "comments_count", "hidden", "created_at")
    list_filter = ("hidden", "visibility")
    list_editable = ("hidden",)
    search_fields = ("body",)

    @admin.display(description="Post")
    def short(self, obj):
        return obj.body[:60]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "body", "hidden", "created_at")
    list_editable = ("hidden",)


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ("post", "comment", "reporter", "reason", "handled", "created_at")
    list_filter = ("handled", "reason")
    list_editable = ("handled",)
