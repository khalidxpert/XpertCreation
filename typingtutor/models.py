import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class Drill(models.Model):
    """
    A piece of text to type. Kept in the database rather than the frontend so
    the client never knows what is coming until the server hands it over -
    which is also what makes the timing trustworthy.
    """

    LESSON = "lesson"
    TEST = "test"
    GAME = "game"
    KINDS = [(LESSON, "Lesson"), (TEST, "Test"), (GAME, "Game")]

    kind = models.CharField(max_length=10, choices=KINDS, default=LESSON)
    level = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=120)
    hint = models.CharField(max_length=200, blank=True, default="")
    content = models.TextField()
    lang = models.CharField(max_length=5, default="en")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["kind", "level", "order", "id"]

    def __str__(self):
        return "%s %d - %s" % (self.kind, self.level, self.title)


class Session(models.Model):
    """
    One attempt, opened by the server.

    started_at is set here, not by the browser. Every score is worked out from
    this timestamp, so a client cannot claim it typed 400 characters in two
    seconds by lying about the clock.
    """

    MIN_SECONDS = 3          # below this, nobody typed anything real
    MAX_SECONDS = 60 * 15    # abandoned sessions expire

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="typing_sessions")
    drill = models.ForeignKey(Drill, on_delete=models.CASCADE)
    token = models.CharField(max_length=32, unique=True, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    @classmethod
    def open(cls, user, drill, ip=None):
        return cls.objects.create(user=user, drill=drill, ip=ip,
                                  token=secrets.token_urlsafe(18)[:32])

    @property
    def elapsed(self):
        end = self.finished_at or timezone.now()
        return (end - self.started_at).total_seconds()


class Score(models.Model):
    MODES = [("lesson", "Lesson"), ("test", "Test"), ("game", "Game")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="typing_scores")
    drill = models.ForeignKey(Drill, on_delete=models.SET_NULL, null=True, blank=True)
    mode = models.CharField(max_length=10, choices=MODES, default="test")

    wpm = models.PositiveSmallIntegerField()
    accuracy = models.PositiveSmallIntegerField()
    correct_chars = models.PositiveIntegerField(default=0)
    typed_chars = models.PositiveIntegerField(default=0)
    seconds = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-wpm", "created_at"]
        indexes = [
            models.Index(fields=["mode", "-wpm"]),
            models.Index(fields=["user", "-created_at"]),
        ]


class Stats(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="typing_stats")
    best_wpm = models.PositiveSmallIntegerField(default=0)
    best_accuracy = models.PositiveSmallIntegerField(default=0)
    total_runs = models.PositiveIntegerField(default=0)
    total_seconds = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveSmallIntegerField(default=0)
    longest_streak = models.PositiveSmallIntegerField(default=0)
    last_day = models.DateField(null=True, blank=True)
    lessons_done = models.JSONField(default=list)

    def record(self, score):
        """Streaks count calendar days, so a run at 23:59 and one at 00:01 are
        two days - which is what a learner expects from a daily streak."""
        today = timezone.localdate()
        if self.last_day is None:
            self.current_streak = 1
        elif self.last_day == today:
            pass
        elif (today - self.last_day).days == 1:
            self.current_streak += 1
        else:
            self.current_streak = 1

        self.last_day = today
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.best_wpm = max(self.best_wpm, score.wpm)
        self.best_accuracy = max(self.best_accuracy, score.accuracy)
        self.total_runs += 1
        self.total_seconds += score.seconds
        self.save()

    @property
    def badge(self):
        w = self.best_wpm
        if w >= 90: return "Master"
        if w >= 70: return "Fast"
        if w >= 50: return "Steady"
        if w >= 30: return "Getting there"
        return "Beginner"
