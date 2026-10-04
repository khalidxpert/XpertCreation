from django.conf import settings
from django.db import models


class Book(models.Model):
    """A free, legal book (public domain or openly licensed) added by staff from a trusted source."""
    CATS = [("urdu", "Urdu classics"), ("islamic", "Islamic"), ("english", "English classics"), ("poetry", "Poetry"), ("children", "Children"), ("learning", "Learning")]
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=160, blank=True, default="")
    year = models.CharField(max_length=12, blank=True, default="")
    lang = models.CharField(max_length=2, default="ur")
    category = models.CharField(max_length=10, choices=CATS, default="urdu")
    description = models.CharField(max_length=600, blank=True, default="")
    source = models.CharField(max_length=12)                 # archive | gutenberg | wikisource
    source_id = models.CharField(max_length=200)
    source_url = models.URLField(max_length=400)
    cover = models.URLField(max_length=400, blank=True, default="")
    rights = models.CharField(max_length=200, blank=True, default="")
    views = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("source", "source_id")]


class SavedBook(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "book")]
