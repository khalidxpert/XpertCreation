from django.db import models


class PostMeta(models.Model):
    """Feeling, check-in and tagged people for a Connect post. Kept apart from the feed's own table."""
    post = models.OneToOneField("feed.Post", on_delete=models.CASCADE, related_name="xmeta")
    feeling = models.CharField(max_length=40, blank=True, default="")
    place = models.CharField(max_length=120, blank=True, default="")
    tagged = models.JSONField(default=list, blank=True)      # user ids
