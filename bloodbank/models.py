from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

BLOOD_GROUPS = [
    ("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
    ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-"),
]

# Who can receive from whom. Used to widen a search rather than narrow it: a
# request for A+ should also reach A-, O+ and O- donors.
CAN_DONATE_TO = {
    "O-":  ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+":  ["O+", "A+", "B+", "AB+"],
    "A-":  ["A-", "A+", "AB-", "AB+"],
    "A+":  ["A+", "AB+"],
    "B-":  ["B-", "B+", "AB-", "AB+"],
    "B+":  ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}


def donors_for(group):
    """Blood groups that can donate to `group`."""
    return [g for g, can in CAN_DONATE_TO.items() if group in can]


def clean_city(value):
    """
    One spelling per city.

    Without this, "lahore", "Lahore " and "LAHORE" become three separate
    cities and a search finds a third of the donors who are actually there.
    """
    s = " ".join(str(value or "").split()).strip(" ,.-")
    return s.title() if s else ""


class Donor(models.Model):
    DEFERRAL_DAYS = 56   # standard whole-blood interval

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="donor")
    name = models.CharField(max_length=120)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    city = models.CharField(max_length=100, db_index=True)
    country = models.CharField(max_length=100, default="Pakistan", db_index=True)

    # Never sent to anyone until this donor accepts a specific request.
    phone = models.CharField(max_length=20)

    # Some donors give a WhatsApp number that is not their calling number.
    whatsapp_number = models.CharField(max_length=20, blank=True, default="")

    # Coordinates are deliberately coarse. Two decimal places is about 1.1 km,
    # which is plenty to sort by distance and not enough to find a house.
    share_location = models.BooleanField(default=False)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    allow_call = models.BooleanField(default=True)
    allow_whatsapp = models.BooleanField(default=True)
    allow_sms = models.BooleanField(default=False)

    is_available = models.BooleanField(
        default=True, help_text="Donor's own switch. Turning it off hides them from searches.")
    last_donation = models.DateField(null=True, blank=True)

    is_verified = models.BooleanField(default=False, help_text="Set by an admin after checking ID.")
    is_blocked = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["city", "blood_group", "is_available"])]

    def save(self, *args, **kwargs):
        self.city = clean_city(self.city)
        self.country = clean_city(self.country) or "Pakistan"
        # Round here rather than in the view: whichever code path writes a
        # location, it can never store a precise one by accident.
        if self.lat is not None:
            self.lat = round(float(self.lat), 2)
        if self.lng is not None:
            self.lng = round(float(self.lng), 2)
        if not self.share_location:
            self.lat = self.lng = None
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s (%s, %s)" % (self.name, self.blood_group, self.city)

    @property
    def eligible_from(self):
        if not self.last_donation:
            return None
        return self.last_donation + timedelta(days=self.DEFERRAL_DAYS)

    @property
    def is_eligible(self):
        """A donor who gave blood three weeks ago must not be asked again. The
        rule is enforced here rather than left to whoever is calling."""
        d = self.eligible_from
        return d is None or timezone.localdate() >= d

    @property
    def can_be_asked(self):
        return (self.is_available and self.is_eligible
                and not self.is_blocked and self.user.is_active)


class Request(models.Model):
    URGENCY = [("normal", "Within a few days"), ("urgent", "Today"), ("critical", "Right now")]
    OPEN, FULFILLED, CANCELLED, EXPIRED = "open", "fulfilled", "cancelled", "expired"
    STATUS = [(OPEN, "Open"), (FULFILLED, "Fulfilled"),
              (CANCELLED, "Cancelled"), (EXPIRED, "Expired")]

    DEFAULT_DAYS = 7

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="blood_requests")
    patient_name = models.CharField(max_length=120, blank=True, default="")
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    units = models.PositiveSmallIntegerField(default=1)
    city = models.CharField(max_length=100, db_index=True)
    hospital = models.CharField(max_length=200)
    urgency = models.CharField(max_length=10, choices=URGENCY, default="urgent")
    note = models.TextField(blank=True, default="")

    contact_phone = models.CharField(max_length=20)

    status = models.CharField(max_length=10, choices=STATUS, default=OPEN, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Requests expire on their own. An open request from three months ago has
    # people ringing a family whose need passed long ago - or worse.
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.city = clean_city(self.city)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=self.DEFAULT_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_live(self):
        return self.status == self.OPEN and timezone.now() < self.expires_at

    def matching_groups(self):
        return donors_for(self.blood_group)


class Ask(models.Model):
    """
    A request reaching one donor, and that donor's answer.

    The number is not in the request and not in the search results. It is
    released here, once, by the donor, to one requester - which is the whole
    point of the design.
    """

    PENDING, ACCEPTED, DECLINED = "pending", "accepted", "declined"
    STATUS = [(PENDING, "Waiting"), (ACCEPTED, "Accepted"), (DECLINED, "Declined")]

    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="asks")
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="asks")
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    answered_at = models.DateTimeField(null=True, blank=True)

    # Kept for accountability: if a donor is harassed, this shows exactly who
    # was given the number and when.
    requester_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = [("request", "donor")]
        ordering = ["-created_at"]

    @property
    def phone_visible(self):
        return self.status == self.ACCEPTED


class Report(models.Model):
    """Someone misusing a released number. Rare, but it has to be possible."""
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="blood_reports")
    ask = models.ForeignKey(Ask, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


def distance_km(a_lat, a_lng, b_lat, b_lng):
    """Great-circle distance. Only meaningful to about a kilometre, which is
    all the stored coordinates support anyway."""
    from math import asin, cos, radians, sin, sqrt
    if None in (a_lat, a_lng, b_lat, b_lng):
        return None
    dlat = radians(b_lat - a_lat)
    dlng = radians(b_lng - a_lng)
    h = (sin(dlat / 2) ** 2
         + cos(radians(a_lat)) * cos(radians(b_lat)) * sin(dlng / 2) ** 2)
    return round(2 * 6371 * asin(sqrt(h)), 1)
