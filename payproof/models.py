"""Pay by JazzCash / Raast: the buyer sends money to our JazzCash Business account, then gives the transaction ID and a
screenshot. The team checks it and approves; the order is then switched on exactly like a gateway payment."""
from django.conf import settings
from django.db import models


class PayAccount(models.Model):
    """One row: where people send money. Editable by the team on /payments-admin."""
    enabled = models.BooleanField(default=True)
    title = models.CharField(max_length=80, default="Xpert Creation")
    bank = models.CharField(max_length=60, default="JazzCash Business")
    till = models.CharField(max_length=30, blank=True)
    iban = models.CharField(max_length=40, blank=True)
    account = models.CharField(max_length=40, blank=True)
    qr = models.TextField(blank=True)              # the text inside the JazzCash / Raast QR code
    note = models.CharField(max_length=300, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class PayProof(models.Model):
    PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
    order = models.ForeignKey("shop.Order", on_delete=models.CASCADE, related_name="proofs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    amount = models.PositiveIntegerField()
    txn = models.CharField(max_length=40)
    sender = models.CharField(max_length=60, blank=True)      # name or number it was paid from
    shot = models.CharField(max_length=120, blank=True)       # file name under the private folder
    status = models.CharField(max_length=10, default=PENDING, db_index=True)
    reason = models.CharField(max_length=200, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
