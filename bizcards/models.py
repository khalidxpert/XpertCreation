from django.conf import settings
from django.db import models
from django.utils import timezone


class Card(models.Model):
    """A digital business card at /c/<slug>. Everything the owner fills in lives in `data` (profile, sections,
    design, QR style), so new section types need no database change. The QR points to the page, so the card
    can change later without reprinting the QR."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bizcards")
    slug = models.SlugField(max_length=40, unique=True)
    data = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)          # moderators
    legacy_token = models.CharField(max_length=24, blank=True, default="", db_index=True)   # old /card/<token> links
    views = models.PositiveIntegerField(default=0)
    scans = models.PositiveIntegerField(default=0)
    saves = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug


class CardStat(models.Model):
    """Daily counts per card: views, scans, contact saves, and clicks on each button."""
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="stats")
    day = models.DateField()
    kind = models.CharField(max_length=10)
    label = models.CharField(max_length=60, blank=True, default="")
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("card", "day", "kind", "label")]
