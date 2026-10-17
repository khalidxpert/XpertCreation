"""Shops and restaurants take payment straight into their own JazzCash / EasyPaisa / bank account.
The buyer pays, uploads the screenshot and transaction ID; the seller checks their account and marks it received.
XpertCreation never holds this money. Screenshots and QR pictures are kept outside the website folder."""
from django.conf import settings
from django.db import models


class SellerPay(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sellerpay")
    on = models.BooleanField(default=False)
    jazzcash = models.CharField(max_length=20, blank=True, default="")
    jazzcash_name = models.CharField(max_length=60, blank=True, default="")
    easypaisa = models.CharField(max_length=20, blank=True, default="")
    easypaisa_name = models.CharField(max_length=60, blank=True, default="")
    bank = models.CharField(max_length=60, blank=True, default="")
    title = models.CharField(max_length=80, blank=True, default="")
    iban = models.CharField(max_length=34, blank=True, default="")
    raast = models.CharField(max_length=40, blank=True, default="")
    qr = models.CharField(max_length=120, blank=True, default="")          # private file name
    note = models.CharField(max_length=200, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)


class Proof(models.Model):
    KINDS = [("store", "Store"), ("food", "Food")]
    kind = models.CharField(max_length=6, choices=KINDS, db_index=True)
    order_id = models.PositiveIntegerField(db_index=True)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    amount = models.PositiveIntegerField()
    txn = models.CharField(max_length=40)
    sender = models.CharField(max_length=60, blank=True, default="")
    shot = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(max_length=8, default="pending", db_index=True)   # pending | ok | bad
    reason = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
