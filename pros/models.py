from django.conf import settings
from django.db import models


class Pro(models.Model):
    """A worker who can be hired: plumber, electrician, AC technician... Only ID-verified (KYC) members."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xpro")
    name = models.CharField(max_length=80)
    services = models.JSONField(default=list)                   # category keys
    city = models.CharField(max_length=60, db_index=True)
    areas = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True, default="")
    about = models.TextField(max_length=2000, blank=True, default="")
    years = models.PositiveSmallIntegerField(default=0)
    rate = models.CharField(max_length=80, blank=True, default="")  # e.g. "Visit Rs 500, then per job"
    photos = models.JSONField(default=list, blank=True)           # work photos under /media/pros/
    available = models.BooleanField(default=True)
    status = models.CharField(max_length=10, default="active", db_index=True)   # active | paused (by team)
    note = models.CharField(max_length=300, blank=True, default="")
    rating_sum = models.PositiveIntegerField(default=0)
    rating_n = models.PositiveIntegerField(default=0)
    jobs_done = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Job(models.Model):
    """A customer's request: post it to all nearby pros, or book one pro directly (pro set, direct=True)."""
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pro_jobs")
    category = models.CharField(max_length=20, db_index=True)
    title = models.CharField(max_length=120)
    details = models.TextField(max_length=2000, blank=True, default="")
    city = models.CharField(max_length=60, db_index=True)
    area = models.CharField(max_length=120, blank=True, default="")
    address = models.CharField(max_length=240, blank=True, default="")     # shown to the hired pro only
    maplink = models.CharField(max_length=300, blank=True, default="")      # shown to the hired pro only
    phone = models.CharField(max_length=20)                                 # shown to the hired pro only
    when = models.CharField(max_length=10, default="asap")
    date = models.DateField(null=True, blank=True)
    budget = models.PositiveIntegerField(default=0)
    photos = models.JSONField(default=list, blank=True)
    direct = models.BooleanField(default=False)
    pro = models.ForeignKey(Pro, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")   # booked / hired pro
    price = models.PositiveIntegerField(default=0)                          # agreed price
    status = models.CharField(max_length=10, default="open", db_index=True)  # open | hired | done | cancelled | expired
    created_at = models.DateTimeField(auto_now_add=True)
    hired_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)


class Offer(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="offers")
    pro = models.ForeignKey(Pro, on_delete=models.CASCADE, related_name="offers")
    price = models.PositiveIntegerField(default=0)        # 0 = "price after seeing the work"
    note = models.CharField(max_length=400, blank=True, default="")
    status = models.CharField(max_length=10, default="sent")   # sent | accepted | declined | withdrawn
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("job", "pro")]


class Review(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="review")
    pro = models.ForeignKey(Pro, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    stars = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=500, blank=True, default="")
    reply = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class Report(models.Model):
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    pro = models.ForeignKey(Pro, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=300)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
