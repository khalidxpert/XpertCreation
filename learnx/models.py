from django.conf import settings
from django.db import models
from django.utils import timezone


class LessonQA(models.Model):
    """A question under one lesson (parent empty) or an answer to it (parent set)."""
    course = models.CharField(max_length=40, db_index=True)
    lesson = models.CharField(max_length=60, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_qa")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="answers")
    body = models.TextField(max_length=1000)
    helpful = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created"]
        indexes = [models.Index(fields=["course", "lesson", "parent"])]

    def __str__(self):
        return "%s/%s: %s" % (self.course, self.lesson, self.body[:40])
