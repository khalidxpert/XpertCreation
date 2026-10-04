from django.conf import settings
from django.db import models

U = settings.AUTH_USER_MODEL


class Clip(models.Model):
    """A short vertical video. processing -> (published | pending review) ; failed ; rejected ; hidden by reports."""
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="clips")
    caption = models.CharField(max_length=300, blank=True, default="")
    status = models.CharField(max_length=10, default="processing", db_index=True)
    note = models.CharField(max_length=300, blank=True, default="")
    src_path = models.CharField(max_length=300, blank=True, default="")
    video_url = models.URLField(max_length=400, blank=True, default="")
    video_key = models.CharField(max_length=300, blank=True, default="")
    thumb_url = models.URLField(max_length=400, blank=True, default="")
    duration = models.FloatField(default=0)
    hidden = models.BooleanField(default=False, db_index=True)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class ClipLike(models.Model):
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = [("user", "clip")]


class ClipComment(models.Model):
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="clip_comments")
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)


class ClipReport(models.Model):
    clip = models.ForeignKey(Clip, on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("clip", "user")]
