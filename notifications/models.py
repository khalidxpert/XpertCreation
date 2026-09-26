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
    pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)
    voice = models.CharField(max_length=200, blank=True, default="")
    voice_secs = models.PositiveSmallIntegerField(default=0)
    attachment = models.CharField(max_length=200, blank=True, default="")
    attachment_name = models.CharField(max_length=120, blank=True, default="")
    attachment_size = models.PositiveIntegerField(default=0)

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


class ChatGroup(models.Model):
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=300, blank=True, default="")
    photo = models.CharField(max_length=160, blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    only_admins_send = models.BooleanField(default=False)
    only_admins_edit = models.BooleanField(default=True)
    invite_code = models.CharField(max_length=16, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    ROLES = [("admin", "Admin"), ("member", "Member")]
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships")
    role = models.CharField(max_length=8, choices=ROLES, default="member")
    last_read_id = models.PositiveIntegerField(default=0)
    muted = models.BooleanField(default=False)
    bot_mod = models.BooleanField(default=False)
    warnings = models.PositiveSmallIntegerField(default=0)
    muted_until = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    msg_count = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("group", "user")]


class GroupInvite(models.Model):
    STATES = [("pending", "Waiting"), ("accepted", "Accepted"), ("declined", "Declined")]
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="invites")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_invites")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=10, choices=STATES, default="pending")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("group", "user")]


class GroupMessage(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    body = models.TextField(max_length=2000, blank=True, default="")
    image = models.CharField(max_length=160, blank=True, default="")
    attachment = models.CharField(max_length=200, blank=True, default="")
    attachment_name = models.CharField(max_length=120, blank=True, default="")
    attachment_size = models.PositiveIntegerField(default=0)
    system = models.BooleanField(default=False)
    bot = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)
    voice = models.CharField(max_length=200, blank=True, default="")
    voice_secs = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]


class GroupPrivacy(models.Model):
    """Who may put this member straight into a group. Anyone else sends an invitation instead."""
    CHOICES = [("everyone", "Everyone"), ("connections", "My connections"), ("nobody", "Nobody")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_privacy")
    who = models.CharField(max_length=12, choices=CHOICES, default="connections")


class GroupBot(models.Model):
    """The group's bot: greets people, keeps order, answers !commands. Set up by the group's admins."""
    group = models.OneToOneField(ChatGroup, on_delete=models.CASCADE, related_name="bot")
    enabled = models.BooleanField(default=True)
    name = models.CharField(max_length=30, default="XpertBot")
    greeting = models.CharField(max_length=300, default="Welcome to {group}, {name}! \U0001F44B Type !help to see what I can do, and !rules for the group rules.")
    rules = models.TextField(max_length=1500, blank=True, default="1. Be kind and respectful.\n2. No spam or advertising.\n3. No abuse or bad language.")
    bad_words = models.TextField(max_length=3000, blank=True, default="")
    warn_limit = models.PositiveSmallIntegerField(default=3)
    mute_minutes = models.PositiveSmallIntegerField(default=30)
    flood_count = models.PositiveSmallIntegerField(default=6)
    flood_seconds = models.PositiveSmallIntegerField(default=10)
    links_admins_only = models.BooleanField(default=False)
    pin_admins_only = models.BooleanField(default=False)


class GroupBan(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="bans")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("group", "user")]


class GroupBotTimer(models.Model):
    """A message the bot posts by itself: every N hours, or every day at a set time."""
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="bot_timers")
    text = models.CharField(max_length=500)
    every_hours = models.PositiveSmallIntegerField(default=0)
    daily_at = models.TimeField(null=True, blank=True)
    next_run = models.DateTimeField(db_index=True)


class GroupBotLog(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="bot_log")
    action = models.CharField(max_length=20)
    target = models.CharField(max_length=120, blank=True, default="")
    by = models.CharField(max_length=120, blank=True, default="")
    reason = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-id"]
