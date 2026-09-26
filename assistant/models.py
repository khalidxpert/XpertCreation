from django.conf import settings
from django.db import models


class AssistantUse(models.Model):
    """How many questions a member asked on a day - for the daily limit and the usage panel.
    What they asked is never stored."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    day = models.DateField(db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "day")]
