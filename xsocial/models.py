"""XpertConnect extras, part 2: photo frames (Open to work / Hiring), polls in posts, birthday and work-anniversary wishes."""
from django.conf import settings
from django.db import models


class Frame(models.Model):
    """'hiring' is kept here; 'open to work' uses the profile's own open_to_work field, so both stay in step."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xs_frame")
    kind = models.CharField(max_length=8, blank=True, default="")      # "" | hiring
    text = models.CharField(max_length=120, blank=True, default="")     # e.g. "Hiring: 2 sales staff"
    updated_at = models.DateTimeField(auto_now=True)


class Poll(models.Model):
    post = models.OneToOneField("feed.Post", on_delete=models.CASCADE, related_name="xs_poll")
    options = models.JSONField(default=list)                          # ["Yes", "No", ...] 2 to 4
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    option = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("poll", "user")]


class Wish(models.Model):
    KINDS = [("birthday", "Birthday"), ("work", "Work anniversary")]
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xs_wishes")
    kind = models.CharField(max_length=10, choices=KINDS)
    year = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("sender", "to", "kind", "year")]


class Ambassador(models.Model):
    """XpertCreation Brand Ambassadors: members apply on /ambassadors, the team approves; approved = badge on profile and posts + blue tick."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xs_ambassador")
    title = models.CharField(max_length=60, default="Brand Ambassador")
    city = models.CharField(max_length=60, blank=True, default="")
    active = models.BooleanField(default=False, db_index=True)              # approved and showing
    status = models.CharField(max_length=10, default="pending", db_index=True)   # pending | approved | rejected | removed
    why = models.TextField(max_length=800, blank=True, default="")            # from the application
    reason = models.CharField(max_length=200, blank=True, default="")         # team's note when rejected
    order = models.PositiveSmallIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "added_at"]
