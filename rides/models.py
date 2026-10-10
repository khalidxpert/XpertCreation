"""XpertCreation Rides - a ride service for women only (women riders, women drivers).
Pilot: live requests like Uber, cash to the driver, car / rickshaw / bike, every city."""
from django.conf import settings
from django.db import models

VEHICLES = [("car", "Car"), ("rickshaw", "Rickshaw"), ("bike", "Bike")]


class Fare(models.Model):
    """Fare per vehicle type. Changed by the team on /rides#team."""
    vehicle = models.CharField(max_length=10, choices=VEHICLES, unique=True)
    base = models.PositiveIntegerField(default=100)
    per_km = models.PositiveIntegerField(default=40)
    minimum = models.PositiveIntegerField(default=150)
    active = models.BooleanField(default=True)


class Rider(models.Model):
    """A rider's own statement that she is a woman, and her contact number."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ride_rider")
    phone = models.CharField(max_length=20)
    agreed_at = models.DateTimeField(auto_now_add=True)
    blocked = models.BooleanField(default=False)
    rating = models.FloatField(default=0)
    ratings = models.PositiveIntegerField(default=0)


class Driver(models.Model):
    PENDING, APPROVED, REJECTED, SUSPENDED, DRAFT = "pending", "approved", "rejected", "suspended", "draft"
    STATES = [(DRAFT, "Draft"), (PENDING, "Waiting for review"), (APPROVED, "Approved"), (REJECTED, "Not approved"), (SUSPENDED, "Suspended")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ride_driver")
    status = models.CharField(max_length=10, choices=STATES, default=DRAFT, db_index=True)
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=60)
    vehicle = models.CharField(max_length=10, choices=VEHICLES)
    make = models.CharField(max_length=60)            # e.g. Suzuki Alto, white
    plate = models.CharField(max_length=20)
    licence_no = models.CharField(max_length=30, blank=True, default="")
    note = models.CharField(max_length=300, blank=True, default="")   # team's note to the driver
    online = models.BooleanField(default=False, db_index=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    loc_at = models.DateTimeField(null=True, blank=True)
    rating = models.FloatField(default=0)
    ratings = models.PositiveIntegerField(default=0)
    rides_done = models.PositiveIntegerField(default=0)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DriverDoc(models.Model):
    KINDS = [("licence", "Driving licence"), ("registration", "Vehicle registration"), ("selfie", "Photo with the vehicle"), ("other", "Other")]
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="docs")
    kind = models.CharField(max_length=14, choices=KINDS)
    path = models.CharField(max_length=200)
    name = models.CharField(max_length=120)
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Ride(models.Model):
    SEARCHING, ACCEPTED, ARRIVED, STARTED, DONE, CANCELLED, EXPIRED = "searching", "accepted", "arrived", "started", "done", "cancelled", "expired"
    STATES = [(SEARCHING, "Finding a driver"), (ACCEPTED, "Driver on the way"), (ARRIVED, "Driver has arrived"), (STARTED, "On the trip"),
              (DONE, "Completed"), (CANCELLED, "Cancelled"), (EXPIRED, "No driver found")]
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rides_taken")
    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name="rides")
    vehicle = models.CharField(max_length=10, choices=VEHICLES)
    status = models.CharField(max_length=10, choices=STATES, default=SEARCHING, db_index=True)
    p_lat = models.FloatField()
    p_lng = models.FloatField()
    p_text = models.CharField(max_length=160, blank=True, default="")
    d_lat = models.FloatField()
    d_lng = models.FloatField()
    d_text = models.CharField(max_length=160, blank=True, default="")
    km = models.FloatField(default=0)
    fare = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=200, blank=True, default="")
    skip = models.JSONField(default=list, blank=True)     # drivers who dropped this ride - not offered it again
    token = models.CharField(max_length=24, unique=True)  # share-my-trip link
    cancel_by = models.CharField(max_length=10, blank=True, default="")
    cancel_reason = models.CharField(max_length=200, blank=True, default="")
    rider_stars = models.PositiveSmallIntegerField(null=True, blank=True)    # the rider's rating of the driver
    driver_stars = models.PositiveSmallIntegerField(null=True, blank=True)   # the driver's rating of the rider
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)


class Report(models.Model):
    """A safety report or SOS from a ride - goes straight to the team."""
    ride = models.ForeignKey(Ride, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    sos = models.BooleanField(default=False)
    text = models.CharField(max_length=600, blank=True, default="")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
