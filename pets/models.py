import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

TAG_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"      # no 0/O or 1/I - easy to read off a tag


def new_tag():
    return "".join(secrets.choice(TAG_ALPHABET) for _ in range(8))


def in_60_days():
    return timezone.now() + timedelta(days=60)


SPECIES = [("dog", "Dog"), ("cat", "Cat"), ("bird", "Bird"), ("rabbit", "Rabbit"), ("other", "Other")]


class Pet(models.Model):
    GENDERS = [("male", "Male"), ("female", "Female"), ("unknown", "Not sure")]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pets")
    name = models.CharField(max_length=60)
    species = models.CharField(max_length=10, choices=SPECIES, default="dog")
    breed = models.CharField(max_length=80, blank=True, default="")
    gender = models.CharField(max_length=8, choices=GENDERS, default="unknown")
    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.CharField(max_length=120, blank=True, default="")      # path under MEDIA_ROOT
    bio = models.TextField(max_length=1000, blank=True, default="")
    tag_code = models.CharField(max_length=12, unique=True, default=new_tag, editable=False)
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    is_lost = models.BooleanField(default=False, db_index=True)
    lost_since = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return "%s (%s)" % (self.name, self.tag_code)


class HealthRecord(models.Model):
    KINDS = [("vaccine", "Vaccine"), ("checkup", "Check-up"), ("deworming", "Deworming"),
             ("medicine", "Medicine"), ("weight", "Weight"), ("other", "Other")]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="records")
    kind = models.CharField(max_length=10, choices=KINDS, default="other")
    title = models.CharField(max_length=150)
    notes = models.TextField(max_length=1000, blank=True, default="")
    weight_kg = models.FloatField(null=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    done = models.BooleanField(default=True)              # False = planned, from the vaccine schedule
    next_due = models.DateField(null=True, blank=True, db_index=True)
    repeat_days = models.PositiveIntegerField(null=True, blank=True)
    reminded_for = models.DateField(null=True, blank=True)  # the next_due we already sent a bell for
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-id"]


class VaccineTemplate(models.Model):
    species = models.CharField(max_length=10, choices=SPECIES)
    vaccine_name = models.CharField(max_length=150)
    due_at_weeks = models.PositiveIntegerField(help_text="Age in weeks when it is due")
    repeat_every_days = models.PositiveIntegerField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        ordering = ["species", "due_at_weeks", "id"]

    def __str__(self):
        return "%s: %s at %d weeks" % (self.species, self.vaccine_name, self.due_at_weeks)


class LostFound(models.Model):
    KINDS = [("lost", "Lost"), ("found", "Found")]
    STATES = [("active", "Active"), ("resolved", "Resolved"), ("expired", "Expired")]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pet_reports")
    pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    kind = models.CharField(max_length=6, choices=KINDS)
    species = models.CharField(max_length=10, choices=SPECIES, default="dog")
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000, blank=True, default="")
    photo = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=60, blank=True, default="", db_index=True)
    where = models.CharField(max_length=200, blank=True, default="")
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATES, default="active", db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=in_60_days)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class FoundNote(models.Model):
    """Left on a pet's tag page by whoever found it. No account needed."""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="found_notes")
    finder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="+")
    message = models.CharField(max_length=500)
    phone = models.CharField(max_length=30, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


class AdoptionPost(models.Model):
    """A pet looking for a new home. Adoption here is always free - selling is not allowed."""
    STATES = [("available", "Available"), ("reserved", "Reserved"), ("adopted", "Adopted"), ("closed", "Closed")]
    GENDERS = [("male", "Male"), ("female", "Female"), ("unknown", "Not sure")]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adoption_posts")
    pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True, related_name="adoption_posts")
    name = models.CharField(max_length=60)
    species = models.CharField(max_length=10, choices=SPECIES, default="cat")
    breed = models.CharField(max_length=80, blank=True, default="")
    gender = models.CharField(max_length=8, choices=GENDERS, default="unknown")
    age_text = models.CharField(max_length=40, blank=True, default="")
    vaccinated = models.BooleanField(default=False)
    neutered = models.BooleanField(default=False)
    photos = models.JSONField(default=list, blank=True)
    country = models.CharField(max_length=2, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="", db_index=True)
    description = models.TextField(max_length=2000)
    status = models.CharField(max_length=10, choices=STATES, default="available", db_index=True)
    hidden = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return "%s (%s, %s)" % (self.name, self.species, self.city)


class AdoptionRequest(models.Model):
    STATES = [("pending", "Waiting"), ("accepted", "Accepted"), ("declined", "Declined"), ("withdrawn", "Withdrawn")]
    post = models.ForeignKey(AdoptionPost, on_delete=models.CASCADE, related_name="requests")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adoption_requests")
    message = models.TextField(max_length=1000)
    status = models.CharField(max_length=10, choices=STATES, default="pending")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("post", "requester")]
        ordering = ["-id"]


class VetClinic(models.Model):
    """Member-added vets. They go public once a moderator approves them."""
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    name = models.CharField(max_length=120)
    country = models.CharField(max_length=2, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, db_index=True)
    address = models.CharField(max_length=250, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    hours = models.CharField(max_length=120, blank=True, default="")
    services = models.CharField(max_length=300, blank=True, default="")
    emergency = models.BooleanField(default=False, help_text="Open for emergencies around the clock")
    map_url = models.URLField(max_length=300, blank=True, default="")
    approved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["city", "name"]

    def __str__(self):
        return "%s, %s" % (self.name, self.city)
