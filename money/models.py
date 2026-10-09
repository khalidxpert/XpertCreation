from django.conf import settings
from django.db import models


class MoneyBook(models.Model):
    """One member's Money page (accounts + entries), stored encrypted. rev goes up by one on every save."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="money_book")
    blob = models.TextField(blank=True, default="")
    rev = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class MoneySnapshot(models.Model):
    """A daily safety copy (last 30 days kept), so a bad import or delete can be undone by staff."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="money_snapshots")
    blob = models.TextField()
    rev = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
