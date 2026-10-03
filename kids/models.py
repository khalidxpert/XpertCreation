from django.db import models


class KidsChannel(models.Model):
    """An official YouTube channel chosen by staff for the Kids page."""
    CATS = [("islamic", "Islamic"), ("learning", "Learning"), ("rhymes", "Rhymes"), ("stories", "Stories"), ("cartoons", "Cartoons")]
    AGES = [("2-5", "2 to 5"), ("6-10", "6 to 10"), ("all", "All ages")]
    channel_id = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120, blank=True, default="")
    category = models.CharField(max_length=10, choices=CATS, default="cartoons")
    age = models.CharField(max_length=5, choices=AGES, default="all")
    active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)
    fetched_at = models.DateTimeField(null=True, blank=True)


class KidsVideo(models.Model):
    channel = models.ForeignKey(KidsChannel, on_delete=models.CASCADE, related_name="videos")
    video_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    published = models.DateTimeField(db_index=True)
    hidden = models.BooleanField(default=False)
