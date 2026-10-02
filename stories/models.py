from django.conf import settings
from django.db import models


class Story(models.Model):
    """A 24-hour status: a photo, or text on a colour. Seen by connections, or by everyone."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories")
    kind = models.CharField(max_length=6, default="photo")          # photo | text
    image = models.CharField(max_length=200, blank=True, default="")
    text = models.CharField(max_length=300, blank=True, default="")
    bg = models.CharField(max_length=12, blank=True, default="")
    audience = models.CharField(max_length=12, default="connections")  # connections | everyone
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("story", "viewer")]
