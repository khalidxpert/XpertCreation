"""Go Live on XpertConnect. The video itself goes through our own LiveKit server (lk.py); this keeps the list of lives."""
from django.conf import settings
from django.db import models


class Live(models.Model):
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lives")
    title = models.CharField(max_length=120)
    room = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=8, default="live", db_index=True)     # live | ended
    started_at = models.DateTimeField(auto_now_add=True)
    beat_at = models.DateTimeField(null=True, blank=True)                     # the host's phone says "still live" every 20 s
    ended_at = models.DateTimeField(null=True, blank=True)
    viewers = models.PositiveIntegerField(default=0)
    peak = models.PositiveIntegerField(default=0)
    hearts = models.PositiveIntegerField(default=0)
    blocked = models.JSONField(default=list, blank=True)                      # identities the host removed

    class Meta:
        ordering = ["-started_at"]
