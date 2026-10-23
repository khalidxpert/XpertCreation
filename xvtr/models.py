"""Video Translate: subtitles and a transcript for a member's own video, in any language.
The video file and its sound are deleted 2 hours after upload; only the subtitle text is kept (30 days)."""
from django.conf import settings
from django.db import models


class Job(models.Model):
    STATES = [("uploading", "Uploading"), ("downloading", "Downloading"), ("queued", "Waiting"), ("working", "Writing subtitles"),
              ("ready", "Ready"), ("failed", "Failed")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    title = models.CharField(max_length=140, default="")
    url = models.CharField(max_length=600, blank=True, default="")
    src_lang = models.CharField(max_length=8, default="auto")         # what the member picked
    lang = models.CharField(max_length=8, blank=True, default="")     # the language the subtitles are in
    want = models.CharField(max_length=8, blank=True, default="")     # first translation asked for
    size = models.BigIntegerField(default=0)
    got = models.BigIntegerField(default=0)                            # bytes received so far
    chunks = models.PositiveIntegerField(default=0)
    ext = models.CharField(max_length=6, default="mp4")
    duration = models.FloatField(default=0)
    status = models.CharField(max_length=12, choices=STATES, default="uploading", db_index=True)
    progress = models.PositiveSmallIntegerField(default=0)             # percent while writing subtitles
    error = models.CharField(max_length=300, blank=True, default="")
    segments = models.JSONField(default=list, blank=True)              # [{"s": 0.0, "e": 2.5, "t": "..."}]
    video_gone = models.BooleanField(default=False)
    minutes = models.FloatField(default=0)                             # audio minutes sent to the AI (for the daily limit)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)                   # the video file is deleted after this
    done_at = models.DateTimeField(null=True, blank=True)


class Track(models.Model):
    """Subtitles of a job in another language."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="tracks")
    lang = models.CharField(max_length=8)
    status = models.CharField(max_length=10, default="queued")         # queued | working | ready | failed
    progress = models.PositiveSmallIntegerField(default=0)
    segments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("job", "lang")]
