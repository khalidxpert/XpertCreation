"""Telegram (@DamaAcademyBot) buyers -> XpertAcademy accounts and course enrolments."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class TgLink(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tg_link")
    tg_id = models.BigIntegerField(unique=True)
    tg_username = models.CharField(max_length=64, blank=True, default="")
    created = models.DateTimeField(default=timezone.now)


class Enrollment(models.Model):
    """A paid course (from the Telegram bot). Later used to unlock paid courses."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tg_enrollments")
    course = models.ForeignKey("academy.Course", on_delete=models.CASCADE, related_name="tg_enrollments")
    source = models.CharField(max_length=20, default="telegram")
    order_id = models.CharField(max_length=40, unique=True)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "course")]


class LoginTicket(models.Model):
    """One-time sign-in link sent in Telegram (7 days)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tg_tickets")
    token_hash = models.CharField(max_length=64, unique=True)
    next_url = models.CharField(max_length=200, default="/academy/")
    expires = models.DateTimeField()
    used = models.DateTimeField(null=True, blank=True)


class Paywall(models.Model):
    """One row. When on, XpertAcademy courses need a purchase, a Telegram enrolment or a coupon.
    Members who started a course before `started` keep it free."""
    on = models.BooleanField(default=True)
    started = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)


class Coupon(models.Model):
    code = models.CharField(max_length=24, unique=True)
    course = models.ForeignKey("academy.Course", on_delete=models.CASCADE, null=True, blank=True, related_name="coupons")   # empty = any course
    max_uses = models.PositiveIntegerField(default=1)
    uses = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    note = models.CharField(max_length=120, blank=True, default="")
    for_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")   # only this member may use it
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created = models.DateTimeField(default=timezone.now)


class CouponUse(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="used_by")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="academy_coupons")
    course = models.ForeignKey("academy.Course", on_delete=models.CASCADE, related_name="+")
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "course")]


class CouponRequest(models.Model):
    OPEN, GRANTED, DECLINED = "open", "granted", "declined"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    course = models.ForeignKey("academy.Course", on_delete=models.CASCADE, related_name="+")
    message = models.CharField(max_length=400, blank=True, default="")
    status = models.CharField(max_length=10, default=OPEN, db_index=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created = models.DateTimeField(default=timezone.now)
    decided = models.DateTimeField(null=True, blank=True)
