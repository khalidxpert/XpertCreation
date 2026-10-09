from django.conf import settings
from django.db import models


class Walk(models.Model):
    """One walk, run or ride recorded on the member's phone: steps, distance, time and the route on the map."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="step_walks")
    kind = models.CharField(max_length=8, default="walk")            # walk | run | cycle
    started_at = models.DateTimeField()
    day = models.DateField(db_index=True)                            # the member's own date when the walk started
    secs = models.PositiveIntegerField(default=0)                    # moving time (pauses not counted)
    steps = models.PositiveIntegerField(default=0)
    steps_est = models.BooleanField(default=False)                   # True when worked out from distance (no motion sensor)
    dist_m = models.PositiveIntegerField(default=0)
    kcal = models.PositiveIntegerField(default=0)
    path = models.JSONField(default=list, blank=True)                # [[lat, lng], ...]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [models.UniqueConstraint(fields=["user", "started_at"], name="steps_walk_once")]


class Prefs(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="step_prefs")
    goal = models.PositiveIntegerField(default=8000)
    height_cm = models.PositiveSmallIntegerField(default=168)
    weight_kg = models.PositiveSmallIntegerField(default=70)
