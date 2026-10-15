from django.db import models
from django.utils import timezone


class LinkPreview(models.Model):
    """Title, description and picture of a web page, so links in posts show a preview card."""
    key = models.CharField(max_length=64, unique=True)        # sha256 of the url
    url = models.URLField(max_length=1000)
    final_url = models.URLField(max_length=1000, blank=True, default="")
    site = models.CharField(max_length=120, blank=True, default="")
    title = models.CharField(max_length=300, blank=True, default="")
    description = models.CharField(max_length=500, blank=True, default="")
    image = models.URLField(max_length=1000, blank=True, default="")
    ok = models.BooleanField(default=False)
    fetched_at = models.DateTimeField(default=timezone.now)
