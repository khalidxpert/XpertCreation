from django.conf import settings
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=60, unique=True)
    website = models.URLField(max_length=300, blank=True, default="")
    helpline = models.CharField(max_length=40, blank=True, default="")


class Terminal(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="terminals")
    city = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=120)
    map_url = models.URLField(max_length=400, blank=True, default="")


class Route(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="routes")
    from_city = models.CharField(max_length=40, db_index=True)
    to_city = models.CharField(max_length=40, db_index=True)
    times = models.JSONField(default=list)              # ["06:00", "07:30"]
    minutes = models.PositiveIntegerField(default=0)
    fare = models.PositiveIntegerField(default=0)
    service = models.CharField(max_length=40, blank=True, default="")
    checked = models.DateField(auto_now=True)
    active = models.BooleanField(default=True)


class Report(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
