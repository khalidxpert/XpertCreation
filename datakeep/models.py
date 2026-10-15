from django.db import models


class KeptRecord(models.Model):
    """A payment record kept after a member deletes their account (tax and refund records).
    No name, email or phone - only what the sale was."""
    kind = models.CharField(max_length=12)              # promote | freelance | store | payout
    no = models.CharField(max_length=30)                # order number
    role = models.CharField(max_length=8, blank=True, default="")   # buyer | seller (of the deleted member)
    item = models.CharField(max_length=160, blank=True, default="")
    amount = models.IntegerField(default=0)
    fee = models.IntegerField(default=0)                # XpertCreation's share
    status = models.CharField(max_length=12, blank=True, default="")
    provider = models.CharField(max_length=20, blank=True, default="")
    provider_ref = models.CharField(max_length=120, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("kind", "no")]
        ordering = ["-id"]
