from django.db import models


class Translation(models.Model):
    """A saved translation, so the same text is only translated once per language."""
    key = models.CharField(max_length=64, unique=True)        # sha256 of target + text
    target = models.CharField(max_length=5)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
