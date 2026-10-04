from django.conf import settings
from django.db import models

U = settings.AUTH_USER_MODEL


class Afsana(models.Model):
    CATS = [("family", "Family"), ("romance", "Romance"), ("social", "Social"), ("islamic", "Islamic"), ("mystery", "Mystery"),
            ("humour", "Humour"), ("real", "Real life"), ("kids", "For children")]
    author = models.ForeignKey(U, on_delete=models.CASCADE, related_name="afsanay")
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=10, choices=CATS, default="family")
    lang = models.CharField(max_length=2, default="ur")
    summary = models.CharField(max_length=300, blank=True, default="")
    hidden = models.BooleanField(default=False, db_index=True)
    complete = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)


class Qist(models.Model):
    afsana = models.ForeignKey(Afsana, on_delete=models.CASCADE, related_name="qists")
    n = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=120, blank=True, default="")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("afsana", "n")]


class Like(models.Model):
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    afsana = models.ForeignKey(Afsana, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = [("user", "afsana")]


class Bookmark(models.Model):
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    afsana = models.ForeignKey(Afsana, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "afsana")]


class Follow(models.Model):
    follower = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    writer = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = [("follower", "writer")]


class Comment(models.Model):
    afsana = models.ForeignKey(Afsana, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    body = models.CharField(max_length=1000)
    hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Report(models.Model):
    afsana = models.ForeignKey(Afsana, on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(U, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
