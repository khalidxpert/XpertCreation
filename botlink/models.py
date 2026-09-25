# -*- coding: utf-8 -*-
"""
Links an XpertCreation account to a Discord or Telegram identity, through a
short-lived code the person types into the bot - not the other way around,
so a stranger can never link an account they do not control by guessing an
ID. This uses the same Discord server and Telegram channel PenFlow already
has a bot in, extended with a command of its own rather than a second bot
process fighting the same token for one connection slot.
"""
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class LinkCode(models.Model):
    DISCORD, TELEGRAM = "discord", "telegram"
    PLATFORMS = [(DISCORD, "Discord"), (TELEGRAM, "Telegram")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="link_codes")
    platform = models.CharField(max_length=10, choices=PLATFORMS)
    code = models.CharField(max_length=8, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["platform", "code"])]

    def save(self, *args, **kwargs):
        if not self.code:
            # Six characters, no ambiguous ones (0/O, 1/I/l) - typed by hand
            # into a chat window, so it has to be readable at a glance.
            alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
            self.code = "".join(secrets.choice(alphabet) for _ in range(6))
        super().save(*args, **kwargs)

    @property
    def expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 600   # 10 minutes


class BotLink(models.Model):
    """The confirmed link, once a code has been used successfully. A user can
    have one Discord link and one Telegram link - not two of the same kind."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="bot_links")
    platform = models.CharField(max_length=10, choices=LinkCode.PLATFORMS)
    external_id = models.CharField(max_length=64)   # Discord user id, or Telegram chat id
    external_name = models.CharField(max_length=100, blank=True, default="")
    linked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "platform")]
