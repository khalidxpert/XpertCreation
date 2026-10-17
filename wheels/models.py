"""XpertWheels: buy and sell used and new cars, bikes and commercial vehicles."""
from django.conf import settings
from django.db import models

KINDS = [("car", "Car"), ("bike", "Bike"), ("commercial", "Commercial")]


class Ad(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wheel_ads")
    kind = models.CharField(max_length=10, choices=KINDS, default="car", db_index=True)
    make = models.CharField(max_length=40, db_index=True)
    model = models.CharField(max_length=60, db_index=True)
    version = models.CharField(max_length=80, blank=True, default="")
    year = models.PositiveSmallIntegerField(db_index=True)
    mileage = models.PositiveIntegerField(default=0)                 # km
    fuel = models.CharField(max_length=10, default="petrol")
    trans = models.CharField(max_length=10, default="manual")         # manual | auto
    engine = models.PositiveIntegerField(default=0)                  # cc
    body = models.CharField(max_length=20, blank=True, default="")
    color = models.CharField(max_length=30, blank=True, default="")
    reg_city = models.CharField(max_length=40, blank=True, default="")   # "" = unregistered
    assembly = models.CharField(max_length=10, default="local")       # local | imported
    condition = models.CharField(max_length=6, default="used")        # used | new
    features = models.JSONField(default=list, blank=True)
    price = models.PositiveIntegerField(db_index=True)
    negotiable = models.BooleanField(default=True)
    city = models.CharField(max_length=60, db_index=True)
    area = models.CharField(max_length=80, blank=True, default="")
    desc = models.TextField(max_length=3000, blank=True, default="")
    images = models.JSONField(default=list, blank=True)
    phone = models.CharField(max_length=20)
    whatsapp = models.BooleanField(default=True)
    status = models.CharField(max_length=8, default="active", db_index=True)   # active | paused | sold | hidden
    note = models.CharField(max_length=300, blank=True, default="")
    views = models.PositiveIntegerField(default=0)
    calls = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    sold_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]


class Offer(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="offers")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wheel_offers")
    amount = models.PositiveIntegerField()
    message = models.CharField(max_length=300, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    reply = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class Report(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="reports")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=300)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
