from django.conf import settings
from django.db import models
from django.utils import timezone


class Job(models.Model):
    WORKPLACE = [("onsite", "On-site"), ("remote", "Remote"), ("hybrid", "Hybrid")]
    KIND = [("full_time", "Full-time"), ("part_time", "Part-time"), ("internship", "Internship"),
            ("freelance", "Freelance"), ("contract", "Contract")]
    PERIOD = [("month", "a month"), ("year", "a year"), ("hour", "an hour"), ("project", "for the project")]

    poster = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs_posted")
    title = models.CharField(max_length=120)
    company = models.CharField(max_length=120)
    country = models.CharField(max_length=2, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    workplace = models.CharField(max_length=8, choices=WORKPLACE, default="onsite")
    kind = models.CharField(max_length=12, choices=KIND, default="full_time")
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=6, default="PKR")
    salary_period = models.CharField(max_length=8, choices=PERIOD, default="month")
    show_salary = models.BooleanField(default=True)
    description = models.TextField(max_length=6000)
    skills = models.JSONField(default=list, blank=True)
    deadline = models.DateField()
    closed = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False, db_index=True, help_text="Hidden by a moderator")
    applicants_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return "%s at %s" % (self.title, self.company)

    @property
    def is_open(self):
        return not self.closed and not self.hidden and self.deadline >= timezone.localdate()


class Application(models.Model):
    STATUS = [("applied", "Applied"), ("shortlisted", "Shortlisted"), ("rejected", "Not selected"), ("withdrawn", "Withdrawn")]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_applications")
    note = models.TextField(max_length=1000, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS, default="applied")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("job", "applicant")]
        ordering = ["-id"]


class JobReport(models.Model):
    REASONS = [("fee", "Asks for money or a fee"), ("scam", "Scam or fake job"), ("wrong", "Wrong or misleading"),
               ("abuse", "Offensive"), ("other", "Something else")]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=8, choices=REASONS)
    note = models.CharField(max_length=500, blank=True, default="")
    handled = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
