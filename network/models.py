from django.conf import settings
from django.db import models
from django.utils import timezone


class ProProfile(models.Model):
    PUBLIC, MEMBERS, HIDDEN = "public", "members", "hidden"
    VISIBILITY = [(PUBLIC, "Public"), (MEMBERS, "Members only"), (HIDDEN, "Hidden")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pro")
    slug = models.SlugField(max_length=60, unique=True)
    headline = models.CharField(max_length=120, blank=True, default="")
    about = models.TextField(max_length=2000, blank=True, default="")
    city = models.CharField(max_length=60, blank=True, default="")
    open_to_work = models.BooleanField(default=False, db_index=True)
    open_to = models.CharField(max_length=120, blank=True, default="")
    visibility = models.CharField(max_length=8, choices=VISIBILITY, default=MEMBERS, db_index=True)
    website = models.URLField(max_length=200, blank=True, default="")
    linkedin = models.URLField(max_length=200, blank=True, default="")
    github = models.URLField(max_length=200, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    socials = models.JSONField(default=dict, blank=True)
    verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug


class Skill(models.Model):
    profile = models.ForeignKey(ProProfile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=40)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("profile", "name")]

    def __str__(self):
        return self.name


class Endorsement(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="endorsements")
    endorser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="endorsements_given")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("skill", "endorser")]


class Experience(models.Model):
    profile = models.ForeignKey(ProProfile, on_delete=models.CASCADE, related_name="experience")
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=60, blank=True, default="")
    start_month = models.PositiveSmallIntegerField(null=True, blank=True)
    start_year = models.PositiveSmallIntegerField()
    end_month = models.PositiveSmallIntegerField(null=True, blank=True)
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)   # empty = still there
    description = models.TextField(max_length=1000, blank=True, default="")

    class Meta:
        ordering = ["-start_year", "-start_month", "-id"]


class Education(models.Model):
    profile = models.ForeignKey(ProProfile, on_delete=models.CASCADE, related_name="education")
    school = models.CharField(max_length=120)
    degree = models.CharField(max_length=100, blank=True, default="")
    field = models.CharField(max_length=100, blank=True, default="")
    start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-end_year", "-start_year", "-id"]


class ProfileReport(models.Model):
    REASONS = [("fake", "Fake profile"), ("spam", "Spam"), ("abuse", "Abusive"), ("other", "Something else")]

    profile = models.ForeignKey(ProProfile, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="profile_reports")
    reason = models.CharField(max_length=10, choices=REASONS)
    note = models.CharField(max_length=500, blank=True, default="")
    handled = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)


class Connection(models.Model):
    """A request from one member to another. Chat opens only once it is accepted."""
    PENDING, ACCEPTED, DECLINED = "pending", "accepted", "declined"
    STATES = [(PENDING, "Pending"), (ACCEPTED, "Accepted"), (DECLINED, "Declined")]

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conn_sent")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conn_received")
    state = models.CharField(max_length=10, choices=STATES, default=PENDING, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("from_user", "to_user")]


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="net_following")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="net_followers")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("follower", "following")]


class VerificationRequest(models.Model):
    PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
    STATES = [(PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected")]

    profile = models.ForeignKey(ProProfile, on_delete=models.CASCADE, related_name="tick_requests")
    state = models.CharField(max_length=10, choices=STATES, default=PENDING, db_index=True)
    followers_at_request = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
