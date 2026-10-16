"""Halal Rishta: marriage profiles for verified members. Photos stay blurred until both sides accept;
then our matchmaker (moderators) calls both families. Contact details are seen only by the matchmaker."""
from django.conf import settings
from django.db import models
from django.utils import timezone

FOR_WHOM = [("self", "Myself"), ("son", "My son"), ("daughter", "My daughter"), ("brother", "My brother"), ("sister", "My sister"), ("relative", "A relative"), ("friend", "A friend")]
GENDER = [("M", "Man"), ("F", "Woman")]
MARITAL = [("never", "Never married"), ("divorced", "Divorced"), ("widowed", "Widowed"), ("separated", "Separated")]
CHILDREN = [("", "-"), ("none", "No children"), ("with", "Children, living with me"), ("notwith", "Children, not living with me")]
SECT = [("", "Prefer not to say"), ("sunni", "Sunni"), ("shia", "Shia"), ("ahlehadith", "Ahl-e-Hadith"), ("deobandi", "Deobandi"), ("barelvi", "Barelvi"), ("other", "Other")]
PRAYER = [("", "-"), ("five", "Prays five times"), ("most", "Prays most prayers"), ("sometimes", "Prays sometimes"), ("learning", "Learning to pray")]
EDU = [("", "-"), ("matric", "Matric"), ("inter", "Intermediate"), ("bachelor", "Bachelor's"), ("master", "Master's"), ("phd", "MPhil / PhD"), ("alim", "Alim / Alima, Hafiz"), ("other", "Other")]
STATUS = [("active", "Shown"), ("hidden", "Hidden by owner"), ("removed", "Removed by our team")]
I_STATUS = [("sent", "Sent"), ("accepted", "Accepted"), ("declined", "Declined"), ("withdrawn", "Withdrawn")]
C_STATUS = [("new", "New - to call"), ("calling", "Calling the families"), ("talking", "Families are talking"), ("meeting", "Families met"),
            ("nikah", "Nikah done - Mubarak!"), ("closed", "Closed - not going ahead")]


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rishta")
    for_whom = models.CharField(max_length=10, choices=FOR_WHOM, default="self")
    name = models.CharField(max_length=40)
    gender = models.CharField(max_length=1, choices=GENDER)
    birth_year = models.PositiveSmallIntegerField()
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    marital = models.CharField(max_length=10, choices=MARITAL, default="never")
    children = models.CharField(max_length=10, choices=CHILDREN, blank=True, default="")
    sect = models.CharField(max_length=12, choices=SECT, blank=True, default="")
    prayer = models.CharField(max_length=10, choices=PRAYER, blank=True, default="")
    city = models.CharField(max_length=60)
    country = models.CharField(max_length=60, default="Pakistan")
    education = models.CharField(max_length=10, choices=EDU, blank=True, default="")
    education_detail = models.CharField(max_length=80, blank=True, default="")
    profession = models.CharField(max_length=80, blank=True, default="")
    languages = models.CharField(max_length=80, blank=True, default="")
    about = models.TextField(max_length=1000, blank=True, default="")
    family = models.TextField(max_length=800, blank=True, default="")
    looking_for = models.TextField(max_length=800, blank=True, default="")
    photo_clear = models.CharField(max_length=200, blank=True, default="")    # private file, never a public URL
    photo_blur = models.CharField(max_length=200, blank=True, default="")     # media path of the blurred copy
    show_photo = models.BooleanField(default=True)
    contact_name = models.CharField(max_length=60, blank=True, default="")    # wali / parent - matchmaker only
    contact_relation = models.CharField(max_length=30, blank=True, default="")
    contact_phone = models.CharField(max_length=24, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS, default="active", db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Interest(models.Model):
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="sent")
    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="received")
    status = models.CharField(max_length=10, choices=I_STATUS, default="sent", db_index=True)
    message = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("sender", "receiver")]


class Case(models.Model):
    """One accepted interest: the matchmaker calls both families and keeps notes here."""
    interest = models.OneToOneField(Interest, on_delete=models.CASCADE, related_name="case")
    status = models.CharField(max_length=10, choices=C_STATUS, default="new", db_index=True)
    note = models.TextField(blank=True, default="")
    assigned = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class Block(models.Model):
    by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="blocks")
    who = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = [("by", "who")]


class Report(models.Model):
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=300)
    handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
