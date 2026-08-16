import hmac
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Email is the login field. There is no username."""

    def _make(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower().strip()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._make(email, password, **extra)

    def create_superuser(self, email, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_email_verified", True)
        return self._make(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=120, blank=True)

    phone = models.CharField(max_length=20, blank=True)

    # Gift card codes are emailed here. Orders are blocked until this is True.
    is_email_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    daily_limit_pkr = models.PositiveIntegerField(default=5000)
    requires_manual_review = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    block_reason = models.CharField(max_length=200, blank=True)

    signup_ip = models.GenericIPAddressField(null=True, blank=True)
    preferred_lang = models.CharField(max_length=5, default="en")

    # A key such as "free3", not a path. The pictures can be re-hosted or
    # replaced with generated ones without rewriting every stored row.
    avatar = models.CharField(max_length=32, blank=True, default="")

    # Day and month only, by default. A birthday needs those two; a year is an
    # age, which is extra information nobody has to hand over to use the site.
    birth_day = models.PositiveSmallIntegerField(null=True, blank=True)
    birth_month = models.PositiveSmallIntegerField(null=True, blank=True)
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    show_birthday = models.BooleanField(default=False)

    # Result of the vibe quiz. A short key, so the creatures can be renamed or
    # replaced without touching a single stored row.
    vibe = models.CharField(max_length=20, blank=True, default="")

    # Two-letter country, from Cloudflare's header at sign-up. Not the IP -
    # a country is enough to say where members are, and an address is not
    # something worth keeping.
    signup_country = models.CharField(max_length=2, blank=True, default="")

    # A leaderboard is public in a way a certificate is not: a certificate
    # shows a name to whoever holds its number, a board shows it to everyone.
    hide_from_leaderboard = models.BooleanField(
        default=False,
        help_text="When set, this user is ranked but never named publicly.")

    date_joined = models.DateTimeField(default=timezone.now)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.email

    @property
    def can_order(self):
        """Single gate every checkout view must call."""
        return self.is_active and self.is_email_verified and not self.is_blocked


class EmailCode(models.Model):
    """
    Six digit code for email verification and password reset.

    The code is never stored. Only an HMAC of it, keyed with SECRET_KEY, so a
    database dump alone cannot be brute forced offline.
    """

    VERIFY = "verify"
    RESET = "reset"
    PURPOSES = [(VERIFY, "Email verification"), (RESET, "Password reset")]

    MAX_ATTEMPTS = 5
    TTL_MINUTES = 10
    RESEND_COOLDOWN_SECONDS = 60

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="codes")
    purpose = models.CharField(max_length=10, choices=PURPOSES)
    code_hmac = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "accounts_email_code"
        indexes = [models.Index(fields=["user", "purpose", "used_at"])]

    @staticmethod
    def _hmac(raw):
        return hmac.new(
            settings.SECRET_KEY.encode(),
            str(raw).encode(),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def issue(cls, user, purpose, ip=None):
        cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        raw = f"{secrets.randbelow(1000000):06d}"
        obj = cls.objects.create(
            user=user,
            purpose=purpose,
            code_hmac=cls._hmac(raw),
            expires_at=timezone.now() + timedelta(minutes=cls.TTL_MINUTES),
            request_ip=ip,
        )
        return obj, raw

    @classmethod
    def can_resend(cls, user, purpose):
        last = (
            cls.objects.filter(user=user, purpose=purpose)
            .order_by("-created_at")
            .first()
        )
        if not last:
            return True, 0
        elapsed = (timezone.now() - last.created_at).total_seconds()
        wait = cls.RESEND_COOLDOWN_SECONDS - elapsed
        return (wait <= 0), max(0, int(wait))

    @classmethod
    def verify(cls, user, purpose, raw):
        obj = (
            cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not obj:
            return False, "no_code"
        if obj.expires_at < timezone.now():
            return False, "expired"
        if obj.attempts >= cls.MAX_ATTEMPTS:
            return False, "too_many_attempts"

        if not hmac.compare_digest(obj.code_hmac, cls._hmac(raw)):
            obj.attempts += 1
            obj.save(update_fields=["attempts"])
            left = cls.MAX_ATTEMPTS - obj.attempts
            return False, f"wrong_code:{left}"

        obj.used_at = timezone.now()
        obj.save(update_fields=["used_at"])
        return True, ""
