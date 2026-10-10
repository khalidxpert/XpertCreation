"""Property listings (sale and rent): members post their house, flat, plot or shop; buyers contact the owner directly.
No payment goes through the site. Owners with a verified ID show a 'Verified' badge. Listings expire after 60 days unless renewed."""
from django.conf import settings
from django.db import models

PURPOSE = [("sale", "For sale"), ("rent", "For rent")]
KINDS = [("house", "House"), ("flat", "Flat / apartment"), ("plot", "Plot"), ("commercial", "Shop / commercial"), ("office", "Office"),
         ("farmhouse", "Farmhouse"), ("room", "Room / portion"), ("land", "Agricultural land")]
UNITS = [("marla", "Marla"), ("kanal", "Kanal"), ("sqft", "Sq. ft."), ("sqyd", "Sq. yd."), ("acre", "Acre")]


class Listing(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="property_listings")
    purpose = models.CharField(max_length=4, choices=PURPOSE, default="sale", db_index=True)
    kind = models.CharField(max_length=12, choices=KINDS, default="house", db_index=True)
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=5000)
    price = models.BigIntegerField()                              # rupees (for rent: per month)
    city = models.CharField(max_length=60, db_index=True)
    locality = models.CharField(max_length=120)                   # society / block / area
    size = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=6, choices=UNITS, default="marla")
    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)
    furnished = models.BooleanField(default=False)
    by_agent = models.BooleanField(default=False)                 # posted by a dealer / agent
    phone = models.CharField(max_length=20)                       # shown to signed-in members only
    images = models.JSONField(default=list, blank=True)          # paths under /media/property/
    status = models.CharField(max_length=8, default="active", db_index=True)   # active | sold | rented | expired
    hidden = models.BooleanField(default=False, db_index=True)    # hidden by the team
    views = models.PositiveIntegerField(default=0)
    reports = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    renewed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-renewed_at", "-id"]


class Report(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="report_rows")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("listing", "user")]
