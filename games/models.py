from django.conf import settings
from django.db import models
from django.utils import timezone


class Score(models.Model):
    """
    One finished game.

    Scores are worked out on the server from the moves that were played, not
    taken from whatever the browser reports. A leaderboard built on numbers
    the client chose is decoration, not a leaderboard.
    """

    MEMORY, TICTAC = "memory", "tictac"
    GAMES = [(MEMORY, "Memory match"), (TICTAC, "Tic-tac-toe")]

    EASY, MEDIUM, HARD = "easy", "medium", "hard"
    LEVELS = [(EASY, "Easy"), (MEDIUM, "Medium"), (HARD, "Hard")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="game_scores")
    game = models.CharField(max_length=10, choices=GAMES, db_index=True)
    level = models.CharField(max_length=10, choices=LEVELS, default=EASY)

    points = models.PositiveIntegerField(default=0)
    seconds = models.PositiveIntegerField(default=0)
    moves = models.PositiveSmallIntegerField(default=0)
    won = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-points", "seconds"]
        indexes = [
            models.Index(fields=["game", "level", "-points"]),
            models.Index(fields=["user", "-created_at"]),
        ]


class Session(models.Model):
    """
    A game in progress, opened by the server.

    The board is dealt here and the clock starts here. Without that a client
    could claim it matched sixteen pairs in two seconds, and there would be no
    way to tell that it had not.
    """

    MAX_SECONDS = 60 * 30

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="game_sessions")
    game = models.CharField(max_length=10)
    level = models.CharField(max_length=10, default="easy")
    token = models.CharField(max_length=32, unique=True, db_index=True)

    # For memory: the shuffled deck. For tic-tac-toe: the moves so far.
    state = models.JSONField(default=dict)

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    @property
    def elapsed(self):
        end = self.finished_at or timezone.now()
        return (end - self.started_at).total_seconds()


class Stats(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="game_stats")
    played = models.PositiveIntegerField(default=0)
    won = models.PositiveIntegerField(default=0)
    best_memory = models.PositiveIntegerField(default=0)
    best_tictac = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveSmallIntegerField(default=0)
    longest_streak = models.PositiveSmallIntegerField(default=0)
    last_day = models.DateField(null=True, blank=True)

    def record(self, score):
        today = timezone.localdate()
        if self.last_day is None or (today - self.last_day).days > 1:
            self.current_streak = 1
        elif (today - self.last_day).days == 1:
            self.current_streak += 1
        self.last_day = today
        self.longest_streak = max(self.longest_streak, self.current_streak)

        self.played += 1
        if score.won:
            self.won += 1
        if score.game == Score.MEMORY:
            self.best_memory = max(self.best_memory, score.points)
        else:
            self.best_tictac = max(self.best_tictac, score.points)
        self.save()
