# -*- coding: utf-8 -*-
"""
A global notification bell and a chat thread, shared across every module
that already has an accept/consent step - donations and the blood bank -
rather than each module inventing its own copy of the same two things.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """
    One bell entry. `kind` and `ref_id` point back at whatever caused it -
    the bell itself does not need to know what a donation or a blood
    request is, only how to describe and link to one.
    """
    KINDS = [
        ("donate_request", "Someone asked for your item"),
        ("donate_accepted", "Your request was accepted"),
        ("donate_new_post", "A new item was posted"),
        ("blood_request", "Someone wants your blood group"),
        ("blood_accepted", "Your request was accepted"),
        ("chat_message", "New message"),
        ("ticket_reply", "Reply on your support ticket"),
        ("review_published", "Your comment was published"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="notifications", db_index=True)
    kind = models.CharField(max_length=20, choices=KINDS)
    text = models.CharField(max_length=200)
    link = models.CharField(max_length=200, blank=True, default="")

    read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class ChatThread(models.Model):
    """
    One conversation, tied to a donation item or a blood request - never
    freestanding. A thread only exists once there is something to talk
    about, and only the two people involved can see it.
    """
    DONATE, BLOOD = "donate", "blood"
    CONTEXTS = [(DONATE, "Donation"), (BLOOD, "Blood request")]

    context = models.CharField(max_length=10, choices=CONTEXTS)
    ref_id = models.PositiveIntegerField()   # DonationItem.id or BloodRequest.id

    a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    a_cleared_at = models.DateTimeField(null=True, blank=True)
    b_cleared_at = models.DateTimeField(null=True, blank=True)
    a_hidden = models.BooleanField(default=False)
    b_hidden = models.BooleanField(default=False)
    disappear_hours = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("context", "ref_id", "a", "b")]
        ordering = ["-updated_at"]

    def other(self, user):
        return self.b if user.id == self.a_id else self.a

    def has(self, user):
        return user.id in (self.a_id, self.b_id)


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)
    image = models.CharField(max_length=160, blank=True, default="")
    system = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]


class ChatBlock(models.Model):
    """One person blocking another. Either side's block stops both from sending."""
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_blocks")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("blocker", "blocked")]


class ChatReport(models.Model):
    REASONS = [("spam", "Spam"), ("abuse", "Abusive or threatening"), ("scam", "Scam or fraud"), ("other", "Something else")]

    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=10, choices=REASONS)
    note = models.CharField(max_length=500, blank=True, default="")
    handled = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


class PushSubscription(models.Model):
    """One phone or browser that agreed to get notifications."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.CharField(max_length=600, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    fails = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    last_ok = models.DateTimeField(null=True, blank=True)


class Broadcast(models.Model):
    """A message from the admins to every member: it lands in each bell and, if asked, on their phones."""
    AUDIENCE = [("all", "All members"), ("verified", "Members with a verified email")]
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    text = models.CharField(max_length=200)
    link = models.CharField(max_length=200, blank=True, default="")
    audience = models.CharField(max_length=10, choices=AUDIENCE, default="all")
    push = models.BooleanField(default=True)
    recipients = models.PositiveIntegerField(default=0)
    devices = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-id"]
