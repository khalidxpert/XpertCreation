from django.conf import settings
from django.db import models


class Room(models.Model):
    """An online carrom table for 2 or 4 players. The board itself (pieces, turn, score) is a JSON document written by
    the player who just shot; version goes up by one on every change so the other players know to update."""
    code = models.CharField(max_length=8, unique=True)
    size = models.PositiveSmallIntegerField(default=2)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carrom_rooms")
    players = models.JSONField(default=list, blank=True)          # [{"id": user id, "name": "...", "seat": 0}]
    status = models.CharField(max_length=8, default="wait")       # wait | play | over
    state = models.JSONField(null=True, blank=True)
    shot = models.JSONField(null=True, blank=True)                # last shot: {"seat", "shot", "start"} for replay
    version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
