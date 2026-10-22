from django.conf import settings
from django.db import models


class Passkey(models.Model):
    """A passkey (WebAuthn credential) a member can sign in with: fingerprint, face or screen lock."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="passkeys")
    cred_id = models.CharField(max_length=400, unique=True)          # base64url
    public_key = models.TextField()                                   # base64url (COSE)
    sign_count = models.BigIntegerField(default=0)
    name = models.CharField(max_length=60, blank=True, default="")
    transports = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
