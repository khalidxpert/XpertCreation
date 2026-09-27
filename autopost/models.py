from django.db import models
from django.utils import timezone


class AutoPost(models.Model):
    """What the official account has posted, so nothing is posted twice."""
    kind = models.CharField(max_length=12, db_index=True)
    key = models.CharField(max_length=200)
    text = models.TextField(blank=True, default="")
    feed_post_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        unique_together = [("kind", "key")]
        ordering = ["-id"]


class OfficialAdded(models.Model):
    """Members already added to the official group once. If they leave, they are never added again."""
    user_id = models.IntegerField(unique=True)
