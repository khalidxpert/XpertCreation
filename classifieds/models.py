"""Classifieds: an OLX-style board inside XpertCreation.

One app, two halves:

* the models here (categories, ads, photos, favourites, reports),
* a small DRF surface under /api/classifieds/ that the page fetches.

Photos are plain FileFields rather than ImageField so the app does not
depend on Pillow being installed on the server.
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    icon = models.CharField(max_length=8, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:90]
        super().save(*args, **kwargs)


class Ad(models.Model):
    CONDITION = [("used", "Used"), ("new", "New")]
    PRICE_TYPE = [("fixed", "Fixed"), ("negotiable", "Negotiable"), ("free", "Free")]
    STATUS = [("active", "Active"), ("sold", "Sold"), ("hidden", "Hidden")]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ads"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="ads")
    title = models.CharField(max_length=120)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    price_type = models.CharField(max_length=12, choices=PRICE_TYPE, default="fixed")
    condition = models.CharField(max_length=8, choices=CONDITION, default="used")
    city = models.CharField(max_length=60)
    area = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=8, choices=STATUS, default="active")
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["city"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return "%s (%s)" % (self.title, self.city)


class AdImage(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="images")
    image = models.FileField(upload_to="ads/%Y/%m/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ad_favorites"
    )
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "ad")]


class Report(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="reports")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ad_reports"
    )
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
