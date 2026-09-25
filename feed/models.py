from django.conf import settings
from django.db import models
from django.utils import timezone

REACTIONS = [("like", "Like"), ("celebrate", "Celebrate"), ("support", "Support"),
             ("love", "Love"), ("insightful", "Insightful"), ("funny", "Funny")]


class Post(models.Model):
    VISIBILITY = [("public", "Everyone"), ("members", "Signed-in members"), ("connections", "Connections only")]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_posts")
    body = models.TextField(max_length=3000, blank=True, default="")
    images = models.JSONField(default=list, blank=True)          # paths under MEDIA_ROOT, at most four
    visibility = models.CharField(max_length=12, choices=VISIBILITY, default="members")
    reactions_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    hidden = models.BooleanField(default=False, db_index=True, help_text="Hidden by a moderator")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return "%s: %s" % (self.author_id, self.body[:40])


class Reaction(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=12, choices=REACTIONS)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("post", "user")]


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    body = models.TextField(max_length=1000)
    hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]


class PostReport(models.Model):
    REASONS = [("spam", "Spam"), ("abuse", "Abusive or hateful"), ("false", "False information"),
               ("nudity", "Nudity or sexual"), ("other", "Something else")]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=10, choices=REASONS)
    note = models.CharField(max_length=500, blank=True, default="")
    handled = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
