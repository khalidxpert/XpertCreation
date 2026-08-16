# -*- coding: utf-8 -*-
"""
Moderator applications, and support tickets.

Applications are held for the super admin to accept or decline - accepting
sets is_moderator on the account, the same flag the earlier system used.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class ModApplication(models.Model):
    PENDING, ACCEPTED, DECLINED = "pending", "accepted", "declined"
    STATES = [(PENDING, "Waiting"), (ACCEPTED, "Accepted"), (DECLINED, "Declined")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="mod_application")
    why = models.TextField(max_length=800)

    # Shown on the public team page only once accepted, and only these three -
    # no email, so the page cannot be scraped for one.
    linkedin = models.URLField(blank=True, default="")
    instagram = models.URLField(blank=True, default="")
    twitter = models.URLField(blank=True, default="")

    state = models.CharField(max_length=10, choices=STATES, default=PENDING, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]


class Ticket(models.Model):
    OPEN, ANSWERED, CLOSED = "open", "answered", "closed"
    STATES = [(OPEN, "Open"), (ANSWERED, "Answered"), (CLOSED, "Closed")]

    LOW, NORMAL, HIGH = "low", "normal", "high"
    PRIORITIES = [(LOW, "Low"), (NORMAL, "Normal"), (HIGH, "High")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="tickets")
    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=PRIORITIES, default=NORMAL)
    state = models.CharField(max_length=10, choices=STATES, default=OPEN, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class TicketMessage(models.Model):
    """One message in a ticket's thread. Either side can write one."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="+")
    # A staff reply is marked, so the thread reads clearly on both sides
    # without guessing from who the author is.
    is_staff = models.BooleanField(default=False)
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]
