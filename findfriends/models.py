from django.conf import settings
from django.db import models


class FindSetting(models.Model):
    """Whether people who already have this member's email or phone number can find them."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="find_setting")
    by_email = models.BooleanField(default=True)
    by_phone = models.BooleanField(default=True)


class ContactHash(models.Model):
    """A member chose 'remember my contacts': each email / phone is kept only as a one-way scrambled code
    (HMAC with the site key), so we can tell them when one of those people joins. They can delete them any time."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contact_hashes")
    h = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "h")]


class JoinTold(models.Model):
    """'X from your contacts joined' was sent once for this pair."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    joined = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("owner", "joined")]
