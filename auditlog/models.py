from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditEvent(models.Model):
    """One thing a member did. Content (messages, posts) is never copied here - only what kind of
    action it was, on which item, when and from where. Kept for 180 days, visible to the super admin only."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=80, db_index=True)
    category = models.CharField(max_length=20, db_index=True, default="other")
    method = models.CharField(max_length=7, blank=True, default="")
    path = models.CharField(max_length=200, blank=True, default="")
    object_id = models.CharField(max_length=40, blank=True, default="")
    status = models.PositiveSmallIntegerField(default=0)
    ip = models.GenericIPAddressField(null=True, blank=True)
    agent = models.CharField(max_length=160, blank=True, default="")
    extra = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self):
        return "%s: %s" % (self.user_id, self.action)
