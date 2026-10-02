from django.conf import settings
from django.db import models


class Match(models.Model):
    """A match members can predict. Added and settled by staff. Points only - no money."""
    team_a = models.CharField(max_length=40)
    team_b = models.CharField(max_length=40)
    series = models.CharField(max_length=80, blank=True, default="")
    starts_at = models.DateTimeField(db_index=True)
    result = models.CharField(max_length=6, blank=True, default="")      # "" | a | b | draw | nr (no result)
    created_at = models.DateTimeField(auto_now_add=True)


class Pick(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="picks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="match_picks")
    pick = models.CharField(max_length=6)                                   # a | b | draw
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("match", "user")]
