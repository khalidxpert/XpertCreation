from django.conf import settings
from django.db import models


class Biller(models.Model):
    """A member's saved bill (company + reference number) with a monthly reminder. Private to its owner."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billers")
    nickname = models.CharField(max_length=40)
    company = models.CharField(max_length=10)
    ref = models.CharField(max_length=24)
    due_day = models.PositiveSmallIntegerField(default=15)
    remind = models.BooleanField(default=True)
    last_reminded = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
