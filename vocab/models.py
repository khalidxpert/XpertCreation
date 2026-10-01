from django.conf import settings
from django.db import models


class Progress(models.Model):
    """One word for one member, in smart-repetition boxes 0-5: a known word comes back later, a missed one sooner."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vocab")
    word = models.PositiveIntegerField()
    box = models.PositiveSmallIntegerField(default=0)
    due = models.DateField()
    seen = models.PositiveIntegerField(default=0)
    right = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "word")]


class Streak(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vocab_streak")
    last_day = models.DateField(null=True, blank=True)
    days = models.PositiveIntegerField(default=0)
    best = models.PositiveIntegerField(default=0)
