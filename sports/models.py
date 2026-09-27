from django.conf import settings
from django.db import models
from django.utils import timezone


class SportsData(models.Model):
    """The latest copy of each feed we fetched (live cricket, football fixtures, tables...). Every visitor reads
    from here, so the free API plans are called on a schedule, not once per visitor."""
    key = models.CharField(max_length=80, unique=True)
    data = models.JSONField(default=dict)
    fetched_at = models.DateTimeField(default=timezone.now)


class ApiUse(models.Model):
    """Requests made to each provider per day, so we stay inside the free limits."""
    provider = models.CharField(max_length=20)
    day = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("provider", "day")]


class Prediction(models.Model):
    """'Who will win?' - one pick per member per match."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    sport = models.CharField(max_length=12)
    match_id = models.CharField(max_length=64, db_index=True)
    pick = models.CharField(max_length=80)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "sport", "match_id")]
