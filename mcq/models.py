from django.conf import settings
from django.db import models


class Attempt(models.Model):
    """One scored attempt per member per day (the daily 10)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mcq_attempts")
    day = models.DateField(db_index=True)
    score = models.PositiveSmallIntegerField(default=0)
    answers = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "day")]
