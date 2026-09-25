# -*- coding: utf-8 -*-
"""
A donation board: people list things they no longer need, others ask for
them. The contact-on-accept pattern is the same one the blood bank uses -
it was built and hardened there first, and there is no reason to invent a
different one here.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class DonationItem(models.Model):
    CATEGORIES = [
        ("books", "Books"),
        ("clothes", "Clothes"),
        ("shoes", "Shoes"),
        ("furniture", "Furniture"),
        ("electronics", "Electronics"),
        ("toys", "Toys"),
        ("kitchen", "Kitchen & household"),
        ("pets", "Pet supplies"),
        ("other", "Other"),
    ]
    CONDITIONS = [
        ("new", "New / unused"),
        ("good", "Good condition"),
        ("fair", "Well used but usable"),
    ]
    AVAILABLE, RESERVED, GIVEN, REMOVED = "available", "reserved", "given", "removed"
    STATES = [(AVAILABLE, "Available"), (RESERVED, "Reserved"),
             (GIVEN, "Given away"), (REMOVED, "Removed")]

    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="donation_items")
    category = models.CharField(max_length=20, choices=CATEGORIES, db_index=True)
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=1000, blank=True, default="")
    condition = models.CharField(max_length=10, choices=CONDITIONS, default="good")
    quantity = models.PositiveSmallIntegerField(default=1)
    city = models.CharField(max_length=60, db_index=True)

    state = models.CharField(max_length=10, choices=STATES, default=AVAILABLE, db_index=True)

    # Never the donor's phone or exact address: only released once a request
    # is accepted, same as the blood bank's Ask flow.
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    given_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category", "state", "city"])]

    def __str__(self):
        return "%s (%s) by %s" % (self.title, self.category, self.donor.email)


class DonationPhoto(models.Model):
    """Up to 3 per item, enforced in the view. A separate table rather than
    a JSON list, so a broken upload never corrupts the others."""
    item = models.ForeignKey(DonationItem, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="donations/%Y/%m/")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]


class DonationRequest(models.Model):
    """
    A request to receive an item. The requester's contact is never shown to
    the donor until the donor accepts - and even then, the donor chooses to
    share it; accepting a request is not the same as sending a phone number.
    """
    PENDING, ACCEPTED, DECLINED, WITHDRAWN = "pending", "accepted", "declined", "withdrawn"
    STATES = [(PENDING, "Waiting"), (ACCEPTED, "Accepted"),
             (DECLINED, "Declined"), (WITHDRAWN, "Withdrawn")]

    item = models.ForeignKey(DonationItem, on_delete=models.CASCADE, related_name="requests")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="donation_requests")
    message = models.CharField(max_length=300, blank=True, default="")
    state = models.CharField(max_length=10, choices=STATES, default=PENDING, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("item", "requester")]
        ordering = ["-created_at"]


class DonationReport(models.Model):
    """A flag on a listing - fake items, inappropriate photos, spam."""
    item = models.ForeignKey(DonationItem, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="+")
    reason = models.CharField(max_length=300)
    created_at = models.DateTimeField(default=timezone.now)
    handled = models.BooleanField(default=False)
