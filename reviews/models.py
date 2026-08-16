from django.conf import settings
from django.db import models
from django.utils import timezone


class Review(models.Model):
    """
    A rating for one of our own modules.

    Stars appear immediately; written comments wait for a look. That split is
    deliberate: a star cannot carry abuse, a spam link or someone's phone
    number, so it can be trusted straight away. Text can carry all three.
    """

    MODULES = [
        ("academy", "XpertAcademy"),
        ("blood", "Blood Bank"),
        ("typing", "Typing Tutor"),
        ("games", "Games"),
        ("birthdays", "Birthday Reminders"),
        ("weather", "Weather"),
        ("zodiac", "Star signs"),
        ("vibe", "Vibe check"),
    ]

    PENDING, PUBLISHED, REJECTED = "pending", "published", "rejected"
    STATES = [(PENDING, "Waiting"), (PUBLISHED, "Published"), (REJECTED, "Rejected")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="reviews")
    module = models.CharField(max_length=20, choices=MODULES, db_index=True)
    stars = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="", max_length=600)

    # Only applies to the comment. The stars count either way.
    state = models.CharField(max_length=10, choices=STATES, default=PENDING, db_index=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # One review per person per module: they can change it, not stack it.
        unique_together = [("user", "module")]
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["module", "state", "-created_at"])]

    def __str__(self):
        return "%s %d\u2605 by %s" % (self.module, self.stars, self.user.email)

    def save(self, *args, **kwargs):
        self.stars = max(1, min(5, int(self.stars or 0)))
        # A review with no words has nothing to moderate.
        if not self.comment.strip():
            self.state = self.PUBLISHED
        super().save(*args, **kwargs)

    @property
    def comment_visible(self):
        return self.state == self.PUBLISHED and bool(self.comment.strip())
