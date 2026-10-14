"""Brand kit: a member's logo design (made in the logo maker) and business details used on the letterhead,
social covers and their shop landing page."""
from django.conf import settings
from django.db import models


class BrandKit(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brand_kit")
    name = models.CharField(max_length=60, blank=True)
    tagline = models.CharField(max_length=80, blank=True)
    data = models.JSONField(default=dict, blank=True)       # logo design: icon, layout, font, colours; letterhead details
    logo = models.CharField(max_length=140, blank=True)      # PNG under MEDIA_ROOT (transparent)
    updated_at = models.DateTimeField(auto_now=True)


class PromoPost(models.Model):
    """New shops, services and properties already announced by the XpertCreation account."""
    kind = models.CharField(max_length=10)                  # shop | gig | property
    ref = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("kind", "ref")]


class ProfileButton(models.Model):
    """Up to two action buttons on a member's XpertConnect profile, like a Facebook Page button:
    WhatsApp, Call, Email, Website, Shop now, Hire me, Book now, Sign up, Order now, Learn more."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile_buttons")
    items = models.JSONField(default=list, blank=True)      # [{"kind", "label", "value"}]
    clicks = models.PositiveIntegerField(default=0)
    daily = models.JSONField(default=dict, blank=True)      # {"2026-10-15": 4} - last 60 days
    updated_at = models.DateTimeField(auto_now=True)
