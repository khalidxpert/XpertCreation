"""Store add-ons: which country a shop sells in, its social links / opening hours (digital shop card),
and dropshipping (a reseller sells a supplier's product; the supplier ships it to the customer)."""
from django.db import models


class Region(models.Model):
    merchant = models.OneToOneField("store.Merchant", on_delete=models.CASCADE, related_name="region")
    country = models.CharField(max_length=2, default="PK", db_index=True)


class Extra(models.Model):
    merchant = models.OneToOneField("store.Merchant", on_delete=models.CASCADE, related_name="extra")
    social = models.JSONField(default=dict, blank=True)      # {"facebook": url, "instagram": url, ..., "whatsapp": number, "website": url}
    hours = models.JSONField(default=dict, blank=True)       # {"mon": ["09:00", "21:00"] or None, ...}
    show_phone = models.BooleanField(default=False)          # shop phone on the digital card


class DropOffer(models.Model):
    """A supplier lets resellers sell this product. price = what the reseller pays per unit."""
    product = models.OneToOneField("store.Product", on_delete=models.CASCADE, related_name="dropoffer")
    on = models.BooleanField(default=True)
    price = models.PositiveIntegerField()


class DropLink(models.Model):
    """product = the reseller's copy in their own shop; source = the supplier's product."""
    product = models.OneToOneField("store.Product", on_delete=models.CASCADE, related_name="droplink")
    source = models.ForeignKey("store.Product", on_delete=models.SET_NULL, null=True, related_name="resold")
    supplier = models.ForeignKey("store.Merchant", on_delete=models.CASCADE, related_name="drop_resellers")
    warned = models.BooleanField(default=False)


class DropOrder(models.Model):
    """order = the customer's order with the reseller; mirror = the order the supplier ships."""
    order = models.OneToOneField("store.Order", on_delete=models.CASCADE, related_name="dropsrc")
    mirror = models.OneToOneField("store.Order", on_delete=models.CASCADE, related_name="dropmirror")
    cost = models.PositiveIntegerField()
    settled = models.BooleanField(default=False)
