from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

KINDS = [("tv", "Drama / series"), ("movie", "Movie")]
YOUTUBE_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")


class WatchItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist")
    kind = models.CharField(max_length=5, choices=KINDS)
    tmdb_id = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    poster = models.CharField(max_length=200, blank=True, default="")
    year = models.CharField(max_length=4, blank=True, default="")
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "kind", "tmdb_id")]
        ordering = ["-added_at"]


class TitleReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="title_reviews")
    kind = models.CharField(max_length=5, choices=KINDS)
    tmdb_id = models.PositiveIntegerField(db_index=True)
    stars = models.PositiveSmallIntegerField()
    text = models.TextField(max_length=1000, blank=True, default="")
    hidden = models.BooleanField(default=False)        # a moderator can hide one
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "kind", "tmdb_id")]
        ordering = ["-updated_at"]


class OfficialLink(models.Model):
    """A link to where a channel itself posts the episodes. YouTube only - no copies, no pirate sites."""
    kind = models.CharField(max_length=5, choices=KINDS, default="tv")
    tmdb_id = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=200, help_text="The drama or movie, for your own reference")
    label = models.CharField(max_length=80, default="Watch on the official channel",
                             help_text="e.g. 'All episodes on HUM TV'")
    url = models.URLField(max_length=300)
    created_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        host = (urlparse(self.url).hostname or "").lower()
        if host not in YOUTUBE_HOSTS:
            raise ValidationError({"url": "Only YouTube links from the official channel are allowed."})

    def __str__(self):
        return "%s - %s" % (self.title, self.label)
