from django.conf import settings
from django.db import models


class Pref(models.Model):
    """A member's interests and privacy choices. Gender is optional and never shown publicly."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xpref")
    gender = models.CharField(max_length=8, blank=True, default="")            # "" | male | female
    find = models.CharField(max_length=12, default="everyone")                 # everyone | same | connections
    requests = models.CharField(max_length=12, default="everyone")             # everyone | same | nobody
    interests = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class GroupRule(models.Model):
    """Women-only or men-only groups."""
    group = models.OneToOneField("notifications.ChatGroup", on_delete=models.CASCADE, related_name="xrule")
    only = models.CharField(max_length=8, default="")                          # "" | male | female
