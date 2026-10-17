from django.conf import settings
from django.db import models


class WelcomeSent(models.Model):
    """One row per member who got the welcome email, so nobody gets it twice."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="welcome_sent")
    sent_at = models.DateTimeField(auto_now_add=True)
