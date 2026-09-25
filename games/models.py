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
    # Points accumulate across every finished game. best_* keeps the single
    # best run; this is the running total, which is what a player watches.
    total_points = models.PositiveIntegerField(default=0)
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
        self.total_points += score.points
        if score.won:
            self.won += 1
        if score.game == Score.MEMORY:
            self.best_memory = max(self.best_memory, score.points)
        else:
            self.best_tictac = max(self.best_tictac, score.points)
        self.save()

class Room(models.Model):
    """
    Do khiladiyon ka khel, do alag device par.

    Chaal server se guzarti hai taake dono ko ek hi halat mile aur baari ka
    faisla ek jagah ho. Tic-tac-toe ki chaal yahin jaanchi jati hai (nau
    khane, aasan). Chess ki chaal browser mein jaanchi jati hai — uska
    engine JavaScript mein hai aur usay Python mein dobara likhna alag
    kaam hai. Dostana khel ke liye ye kaafi hai; agar kabhi inaam ya
    leaderboard jura to engine server par lana parega.
    """
    OPEN = "open"          # banaya gaya, doosre ka intezar
    PLAYING = "playing"
    OVER = "over"

    code = models.CharField(max_length=8, unique=True, db_index=True)
    game = models.CharField(max_length=10)          # "chess" ya "tictac"
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="rooms_hosted")
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="rooms_joined", null=True, blank=True)
    stage = models.CharField(max_length=10, default=OPEN)
    # Khel ki poori halat. Chess: {fen-jaisi cheez, moves[]}. Tictac: {cells}.
    state = models.JSONField(default=dict)
    turn = models.CharField(max_length=8, default="host")   # host ya guest
    result = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    moved_at = models.DateTimeField(default=timezone.now)

    # Each side stamps this every time it asks for the state. Silence
    # means they closed the tab, and the other one deserves to be told
    # rather than sitting there waiting for a move.
    host_seen = models.DateTimeField(null=True, blank=True)
    guest_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    AWAY_SECONDS = 30

    def here(self, side):
        """Was this side asking for the state a moment ago?"""
        seen = self.host_seen if side == "host" else self.guest_seen
        if not seen:
            return False
        return (timezone.now() - seen).total_seconds() <= self.AWAY_SECONDS

    @property
    def stale(self):
        """Aadha ghanta khamoshi ke baad room chhor diya gaya samjha jaye."""
        return (timezone.now() - self.moved_at).total_seconds() > 60 * 30

    def side_of(self, user):
        if self.host_id == user.id:
            return "host"
        if self.guest_id and self.guest_id == user.id:
            return "guest"
        return None
