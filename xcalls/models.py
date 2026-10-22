from django.conf import settings
from django.db import models
from django.utils import timezone


class Call(models.Model):
    KINDS = [("t", "One-to-one chat"), ("g", "Group"), ("m", "XpertMeet meeting")]
    STATES = [("ringing", "Ringing"), ("live", "Live"), ("ended", "Ended"), ("missed", "Missed"), ("declined", "Declined")]
    kind = models.CharField(max_length=1, choices=KINDS)
    ref_id = models.PositiveIntegerField(db_index=True)          # ChatThread.id or ChatGroup.id (0 for meetings)
    code = models.CharField(max_length=16, blank=True, default="", db_index=True)   # meeting link code
    title = models.CharField(max_length=80, blank=True, default="")
    starts_at = models.DateTimeField(null=True, blank=True)      # scheduled meeting time (XpertMeet)
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    video = models.BooleanField(default=False)
    state = models.CharField(max_length=9, choices=STATES, default="ringing", db_index=True)
    created = models.DateTimeField(default=timezone.now, db_index=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return "%s call %s/%s (%s)" % ("video" if self.video else "voice", self.kind, self.ref_id, self.state)


class CallMember(models.Model):
    STATES = [("ringing", "Ringing"), ("joined", "In the call"), ("left", "Left"), ("declined", "Declined")]
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    state = models.CharField(max_length=9, choices=STATES, default="ringing")
    joined_at = models.DateTimeField(null=True, blank=True)
    seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("call", "user")]


class Signal(models.Model):
    """WebRTC set-up messages (offer, answer, network candidates) passed between the people in a call."""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="signals")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=8)
    data = models.TextField(max_length=20000)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["call", "to", "id"])]
