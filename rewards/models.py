"""Rewards campaign: points for real use of the site. Stage 1 = points and leaderboard.
The wheel, scratch cards, referrals and payouts come in later stages."""
from django.conf import settings
from django.db import models


class Campaign(models.Model):
    """One row. Off until switched on with: manage.py rewards_campaign on --start YYYY-MM-DD --days 30.
    While off (or after it ends) only staff accounts earn points, so it can be tested."""
    enabled = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    budget = models.PositiveIntegerField(default=10000)          # rupees, used by the prize stages
    updated_at = models.DateTimeField(auto_now=True)


class PointEvent(models.Model):
    """One reason a member got points (a post, a lesson, 10 minutes of activity...).
    ref names the thing, so the same post or lesson is never counted twice."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    day = models.DateField(db_index=True)
    kind = models.CharField(max_length=12)
    ref = models.CharField(max_length=100)
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "kind", "ref")]
        indexes = [models.Index(fields=["day", "user"]), models.Index(fields=["kind", "day"])]


class DailyActivity(models.Model):
    """Active seconds per member per day: the tab was visible and used in the last minute."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    day = models.DateField(db_index=True)
    active_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "day")]
