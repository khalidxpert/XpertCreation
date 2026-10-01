from django.db import models
from django.utils import timezone


class Listing(models.Model):
    """A group its admins chose to show in the public groups directory (groups are private otherwise)."""
    group = models.OneToOneField("notifications.ChatGroup", on_delete=models.CASCADE, related_name="listing")
    listed = models.BooleanField(default=True, db_index=True)
    listed_at = models.DateTimeField(default=timezone.now)
