"""Up to 3 pinned pages per member (any tool or section), shown first in the menu and at the top of the home page."""
from django.conf import settings
from django.db import models


class Pin(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pins")
    items = models.JSONField(default=list, blank=True)     # [{"path": "/tools/bmi", "label": "BMI calculator"}]
    updated_at = models.DateTimeField(auto_now=True)
