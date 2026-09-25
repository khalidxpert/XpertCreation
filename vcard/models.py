# -*- coding: utf-8 -*-
"""
A digital visiting card, built from the account. One per user - editing it
replaces the old one rather than piling up drafts.
"""
from django.conf import settings
from django.db import models


class VisitingCard(models.Model):
    THEMES = [
        ("ink", "Midnight"), ("emerald", "Emerald"),
        ("rose", "Rose"), ("amber", "Amber"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="visiting_card")

    display_name = models.CharField(max_length=100, blank=True, default="")
    role = models.CharField(max_length=100, blank=True, default="")
    org = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=60, blank=True, default="")

    # Contact fields are opt-in per field: a card is meant to be shared
    # widely, and someone should be able to leave a phone number off while
    # still keeping their email on it.
    show_phone = models.BooleanField(default=False)
    show_email = models.BooleanField(default=True)
    show_whatsapp = models.BooleanField(default=False)
    phone = models.CharField(max_length=32, blank=True, default="")
    whatsapp = models.CharField(max_length=32, blank=True, default="")

    linkedin = models.URLField(blank=True, default="")
    instagram = models.URLField(blank=True, default="")
    twitter = models.URLField(blank=True, default="")
    website = models.URLField(blank=True, default="")

    theme = models.CharField(max_length=12, choices=THEMES, default="ink")

    # A short, guessable-resistant slug for the public URL: /card/<token>
    token = models.SlugField(max_length=24, unique=True, editable=False)

    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(9).replace("_", "").replace("-", "")[:12]
        super().save(*args, **kwargs)
