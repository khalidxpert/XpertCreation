from django.conf import settings
from django.db import models


class DailyAyah(models.Model):
    """The Ayah of the day, fetched once from AlQuran Cloud and kept."""
    day = models.DateField(unique=True)
    ref = models.CharField(max_length=10)
    surah = models.CharField(max_length=80, default="")
    arabic = models.TextField()
    urdu = models.TextField(blank=True, default="")
    english = models.TextField(blank=True, default="")
    hijri = models.CharField(max_length=80, blank=True, default="")


class Recipe(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recipes")
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=20, default="main")      # main | rice | snack | sweet | side | bread
    serves = models.PositiveSmallIntegerField(default=4)
    minutes = models.PositiveSmallIntegerField(default=30)
    intro = models.CharField(max_length=300, blank=True, default="")
    ingredients = models.JSONField(default=list)                     # [[amount, unit, name], ...]
    steps = models.JSONField(default=list)
    photo = models.CharField(max_length=200, blank=True, default="")
    approved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
