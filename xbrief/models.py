"""My Briefcase: a member's own documents (degrees, experience letters, ID card, passport...).
The files are encrypted on disk outside the web root (store.py); only the owner can open them,
or someone holding a share link the owner made (it stops working after the time they chose)."""
from django.conf import settings
from django.db import models

BUILTIN = [
    ("edu", "Education", "\U0001F393", "تعلیمی اسناد"),
    ("exp", "Experience letters", "\U0001F4BC", "تجربے کے خطوط"),
    ("id", "ID card & passport", "\U0001FAAA", "شناختی کارڈ اور پاسپورٹ"),
    ("cert", "Certificates", "\U0001F4DC", "سرٹیفکیٹ"),
    ("med", "Medical", "\U0001FA7A", "میڈیکل"),
    ("prop", "Property", "\U0001F3E0", "جائیداد"),
    ("other", "Other", "\U0001F4C1", "دیگر"),
]
BUILTIN_KEYS = [b[0] for b in BUILTIN]


class Folder(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brief_folders")
    name = models.CharField(max_length=40)
    icon = models.CharField(max_length=8, default="\U0001F4C2")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]


class Doc(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brief_docs")
    folder = models.CharField(max_length=20, default="other")       # a BUILTIN key, or "f<Folder id>"
    title = models.CharField(max_length=120)
    note = models.CharField(max_length=300, blank=True, default="")
    fname = models.CharField(max_length=120, default="document")
    mime = models.CharField(max_length=80)
    size = models.PositiveIntegerField(default=0)
    path = models.CharField(max_length=80, unique=True)              # name of the encrypted file in the store
    num = models.TextField(blank=True, default="")                   # card / passport number, encrypted (store.enc_text)
    expires = models.DateField(null=True, blank=True)
    reminded = models.CharField(max_length=40, blank=True, default="")  # stages already sent: "60,30"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "folder"]), models.Index(fields=["expires"])]


class Share(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE, related_name="shares")
    token = models.CharField(max_length=48, unique=True)
    expires_at = models.DateTimeField()
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
