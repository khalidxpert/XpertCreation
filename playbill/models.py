from django.conf import settings
from django.db import models
from django.utils import timezone


class PlayPurchase(models.Model):
    """One Google Play purchase. The token is unique, so it can never pay for two orders."""
    token = models.CharField(max_length=600, unique=True)
    sku = models.CharField(max_length=80)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    order = models.ForeignKey("shop.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="play_purchases")
    gp_order = models.CharField(max_length=80, blank=True, default="")     # GPA.xxxx-xxxx
    state = models.CharField(max_length=12, default="new")                # new | paid | consumed | bad
    note = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s %s %s" % (self.sku, self.state, self.gp_order)
