import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Course(models.Model):
    slug = models.SlugField(max_length=40, unique=True)
    title = models.CharField(max_length=120)
    icon = models.CharField(max_length=8, blank=True, default="")
    accent = models.CharField(max_length=9, default="#1B4DFF")
    blurb = models.TextField(blank=True, default="")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    quiz_questions = models.PositiveSmallIntegerField(
        default=8, help_text="How many questions to draw from the pool per attempt.")
    pass_percent = models.PositiveSmallIntegerField(default=70)
    min_lessons_percent = models.PositiveSmallIntegerField(
        default=80, help_text="Percent of lessons done before the quiz unlocks.")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Lesson(models.Model):
    """
    Mirrors the lesson content that ships in the frontend file.

    `key` is a stable identifier, NOT the position. Progress is stored against
    the key, so reordering or inserting lessons never silently reassigns
    somebody's completed work to a different lesson.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    key = models.SlugField(max_length=60)
    title = models.CharField(max_length=160)
    minutes = models.PositiveSmallIntegerField(default=5)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("course", "key")]

    def __str__(self):
        return "%s/%s" % (self.course.slug, self.key)


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "lesson")]
        indexes = [models.Index(fields=["user", "lesson"])]


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    explanation = models.TextField(
        blank=True, default="",
        help_text="Shown after grading. This is where the actual teaching happens.")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:60]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:50]


class Attempt(models.Model):
    """
    One sitting of the quiz.

    The chosen question ids are frozen at start. Without that, a student could
    reload until they get an easy draw, or answer questions never served.
    """

    COOLDOWN_MINUTES = 30
    EXPIRY_MINUTES = 45

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="attempts")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attempts")
    question_ids = models.JSONField(default=list)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    passed = models.BooleanField(default=False)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["user", "course", "-started_at"])]

    @property
    def percent(self):
        return round(self.score / self.total * 100) if self.total else 0

    @property
    def is_expired(self):
        return timezone.now() > self.started_at + timedelta(minutes=self.EXPIRY_MINUTES)


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    was_correct = models.BooleanField(default=False)

    class Meta:
        unique_together = [("attempt", "question")]


def _make_serial():
    """
    Human-readable but not guessable: XC-A7K2-9QM4-3TZP.

    Ambiguous characters are excluded so someone reading it off a printout
    does not confuse O with 0 or I with 1.
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    blocks = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "XC-" + "-".join(blocks)


class Certificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="certificates")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="certificates")
    attempt = models.ForeignKey(Attempt, on_delete=models.SET_NULL, null=True, blank=True)

    serial = models.CharField(max_length=20, unique=True, db_index=True)

    # Snapshot at issue time. If the learner later changes their display name,
    # the certificate must still show the name it was issued under.
    holder_name = models.CharField(max_length=140)
    course_title = models.CharField(max_length=140)
    score_percent = models.PositiveSmallIntegerField(default=0)

    issued_at = models.DateTimeField(default=timezone.now)
    revoked = models.BooleanField(default=False)
    revoked_reason = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["-issued_at"]
        unique_together = [("user", "course")]

    def save(self, *args, **kwargs):
        if not self.serial:
            for _ in range(8):
                candidate = _make_serial()
                if not Certificate.objects.filter(serial=candidate).exists():
                    self.serial = candidate
                    break
            else:
                raise RuntimeError("Could not allocate a unique certificate serial")
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s - %s" % (self.serial, self.holder_name)
