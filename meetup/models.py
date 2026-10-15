"""Meetup groups (ported from PenFlow's Meetup module): groups by city and topic, members, meetups with seats and a map pin."""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

CATEGORIES = [("tech", "Tech & programming"), ("business", "Business & networking"), ("career", "Careers & freelancing"),
              ("sports", "Sports & fitness"), ("arts", "Arts & culture"), ("food", "Food & drink"),
              ("education", "Learning & languages"), ("religion", "Faith & community"), ("social", "Social & hobbies"),
              ("other", "Other")]


def _unique_slug(model, text, max_len=80):
    base = slugify(text)[:max_len] or "meetup"
    s, n = base, 1
    while model.objects.filter(slug=s).exists():
        n += 1; s = "%s-%d" % (base[:max_len - 6], n)
    return s


class MeetGroup(models.Model):
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meet_groups")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    category = models.CharField(max_length=12, choices=CATEGORIES, default="other")
    about = models.TextField(max_length=3000, blank=True, default="")
    city = models.CharField(max_length=60, blank=True, default="", db_index=True)
    cover = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    members_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *a, **k):
        if not self.slug:
            self.slug = _unique_slug(MeetGroup, self.name)
        super().save(*a, **k)

    def __str__(self):
        return self.name


class MeetMember(models.Model):
    group = models.ForeignKey(MeetGroup, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meet_memberships")
    role = models.CharField(max_length=10, default="member")        # organizer | member
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("group", "user")]


class Meetup(models.Model):
    group = models.ForeignKey(MeetGroup, on_delete=models.CASCADE, related_name="meetups")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meetups_organized")
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    about = models.TextField(max_length=4000, blank=True, default="")
    cover = models.CharField(max_length=200, blank=True, default="")
    is_online = models.BooleanField(default=False)
    place = models.CharField(max_length=200, blank=True, default="")     # address / venue
    city = models.CharField(max_length=60, blank=True, default="", db_index=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    online_link = models.URLField(blank=True, default="")
    starts_at = models.DateTimeField(db_index=True)
    minutes = models.PositiveIntegerField(default=120)
    seats = models.PositiveIntegerField(default=50)                       # 0 = no limit
    is_active = models.BooleanField(default=True, db_index=True)
    cancelled = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    reminded_day = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["starts_at"]

    def save(self, *a, **k):
        if not self.slug:
            self.slug = _unique_slug(Meetup, self.title)
        super().save(*a, **k)

    def going(self):
        return self.rsvps.filter(status="going").count()

    def __str__(self):
        return "%s (%s)" % (self.title, self.starts_at.date())


class MeetRsvp(models.Model):
    meetup = models.ForeignKey(Meetup, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meet_rsvps")
    status = models.CharField(max_length=10, default="going")             # going | waitlist | cancelled
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("meetup", "user")]


class MeetReview(models.Model):
    meetup = models.ForeignKey(Meetup, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("meetup", "user")]
