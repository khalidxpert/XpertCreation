"""Social extras for XpertConnect: saved posts, reposts, who viewed my profile, followed hashtags."""
from django.conf import settings
from django.db import models


class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey("feed.Post", on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = [("user", "post")]


class Repost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    post = models.OneToOneField("feed.Post", on_delete=models.CASCADE, related_name="repost_of")      # the new post
    original = models.ForeignKey("feed.Post", on_delete=models.CASCADE, related_name="reposts")
    created_at = models.DateTimeField(auto_now_add=True)


class ProfileView(models.Model):
    """One row per viewer per day. viewer is empty for guests and for members who browse privately."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile_views")
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    vkey = models.CharField(max_length=40)        # user id, or "anon:<hash>"
    day = models.DateField(db_index=True)
    n = models.PositiveIntegerField(default=1)
    last = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("owner", "vkey", "day")]


class SocialSetting(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_setting")
    private_views = models.BooleanField(default=False)     # visit profiles without showing my name


class TagFollow(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tag_follows")
    tag = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "tag")]
