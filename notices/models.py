from django.conf import settings
from django.db import models


class Notice(models.Model):
    """A government job, exam result, admission or scholarship, added by staff from an official source."""
    KINDS = [("job", "Govt job"), ("result", "Result"), ("admission", "Admission"), ("scholarship", "Scholarship")]
    kind = models.CharField(max_length=12, choices=KINDS, db_index=True)
    title = models.CharField(max_length=160)
    org = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    last_date = models.DateField(null=True, blank=True)
    link = models.URLField(max_length=400)
    details = models.TextField(max_length=2000, blank=True, default="")
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
