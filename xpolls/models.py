from django.conf import settings
from django.db import models
from django.utils import timezone


class Poll(models.Model):
    kind = models.CharField(max_length=1, choices=[("t", "Chat"), ("g", "Group")])
    ref_id = models.PositiveIntegerField(db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    question = models.CharField(max_length=200)
    options = models.JSONField(default=list)
    multi = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    option = models.PositiveSmallIntegerField()
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("poll", "user", "option")]
