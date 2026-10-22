from django.conf import settings
from django.db import models
from django.utils import timezone


class GroupRole(models.Model):
    """A named, coloured role inside one XpertChat group (like Discord). Admins make them and give them out."""
    group = models.ForeignKey("notifications.ChatGroup", on_delete=models.CASCADE, related_name="xroles")
    name = models.CharField(max_length=30)
    color = models.CharField(max_length=7, default="#5865F2")
    icon = models.CharField(max_length=8, blank=True, default="")
    position = models.PositiveSmallIntegerField(default=0)      # 0 = top
    hoist = models.BooleanField(default=True)                    # show its members in their own section of the member list
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return "%s (%s)" % (self.name, self.group_id)


class GroupRoleMember(models.Model):
    role = models.ForeignKey(GroupRole, on_delete=models.CASCADE, related_name="holders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = [("role", "user")]
