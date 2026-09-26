from django.conf import settings
from django.db import models


class FindSetting(models.Model):
    """Whether people who already have this member's email or phone number can find them.
    The contacts people check are never stored."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="find_setting")
    by_email = models.BooleanField(default=True)
    by_phone = models.BooleanField(default=True)
