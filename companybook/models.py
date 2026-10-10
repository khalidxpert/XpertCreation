"""XpertCreation's own register: every rupee the company earns or spends, from every platform.
Automatic lines are copied from the shop (Promote items, ads, merchant plans), the freelance marketplace and store
commissions, rewards payouts and referral commissions. The team adds everything else by hand (hosting, salaries...)."""
from django.conf import settings
from django.db import models


class Entry(models.Model):
    day = models.DateField(db_index=True)
    kind = models.CharField(max_length=7, db_index=True)                 # income | expense
    source = models.CharField(max_length=12, db_index=True)              # shop | market | store | rewards | manual
    category = models.CharField(max_length=60, db_index=True)
    amount = models.PositiveIntegerField()                               # rupees
    ref = models.CharField(max_length=60, unique=True, null=True, blank=True)   # e.g. "shop:123" for automatic lines
    note = models.CharField(max_length=300, blank=True, default="")
    test = models.BooleanField(default=False, db_index=True)             # from test / sandbox payments (no real money)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-day", "-id"]
