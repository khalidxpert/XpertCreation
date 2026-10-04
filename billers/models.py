from django.conf import settings
from django.db import models


class Biller(models.Model):
    """A member's saved bill (company + reference number) with a monthly reminder. Private to its owner."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billers")
    nickname = models.CharField(max_length=40)
    company = models.CharField(max_length=20)
    country = models.CharField(max_length=2, default="PK")
    label = models.CharField(max_length=60, blank=True, default="")      # company name for "Other company"
    link = models.URLField(max_length=300, blank=True, default="")      # bill page for "Other company"
    ref = models.CharField(max_length=24)
    due_day = models.PositiveSmallIntegerField(default=15)
    remind = models.BooleanField(default=True)
    last_reminded = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
