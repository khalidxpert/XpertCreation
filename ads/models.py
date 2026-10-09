"""Ad tracking for paid promotions. The purchase itself is shop.Order; this app only counts."""
from django.conf import settings
from django.db import models


class AdEvent(models.Model):
    """One counted view or click. Raw rows are deleted after 30 days (ads_prune); daily totals stay."""
    order = models.ForeignKey("shop.Order", on_delete=models.CASCADE, related_name="ad_events")
    kind = models.CharField(max_length=5)                       # view | click
    placement = models.CharField(max_length=20, default="feed")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    visitor = models.CharField(max_length=32, db_index=True)    # "u<id>" or a hash of IP + browser, never the raw IP
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class AdDailyStat(models.Model):
    order = models.ForeignKey("shop.Order", on_delete=models.CASCADE, related_name="ad_days")
    day = models.DateField()
    views = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("order", "day")]
