from django.conf import settings
from django.db import models


class ShopSetting(models.Model):
    """One row: payments mode (off | test | live) and staff price overrides {"product:plan": rupees}."""
    mode = models.CharField(max_length=6, default="off")
    prices = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class Order(models.Model):
    """One purchase. Paid per order: no stored balance."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    product = models.CharField(max_length=20, db_index=True)
    plan = models.CharField(max_length=10)
    target_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    target_label = models.CharField(max_length=160, blank=True, default="")
    amount = models.PositiveIntegerField()                         # rupees
    status = models.CharField(max_length=10, default="pending", db_index=True)   # pending | paid | cancelled | refunded
    provider = models.CharField(max_length=20, blank=True, default="")
    provider_ref = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    note = models.CharField(max_length=300, blank=True, default="")
