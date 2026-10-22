"""Hotels, guest houses and tour packages on XpertCreation (xpertcreation.com/hotels, /tours).
Only KYC-verified companies list; the team approves each listing. Guests book free and pay at the hotel / to the operator."""
from django.conf import settings
from django.db import models

STATES = [("pending", "Waiting for review"), ("approved", "Live"), ("rejected", "Not approved"), ("hidden", "Hidden by owner")]


class Property(models.Model):
    KINDS = [("hotel", "Hotel"), ("guesthouse", "Guest house"), ("resort", "Resort"), ("apartment", "Apartment"), ("hostel", "Hostel"), ("camp", "Camp / huts")]
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="properties")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="properties")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=90, unique=True)
    kind = models.CharField(max_length=12, choices=KINDS, default="hotel")
    stars = models.PositiveSmallIntegerField(default=0)                 # 0 = not rated
    city = models.CharField(max_length=60, db_index=True)
    area = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=2, default="PK")
    address = models.CharField(max_length=240, blank=True, default="")
    map_url = models.CharField(max_length=300, blank=True, default="")
    about = models.TextField(blank=True, default="")
    amenities = models.JSONField(default=list, blank=True)
    photos = models.JSONField(default=list, blank=True)                # paths under MEDIA_ROOT
    phone = models.CharField(max_length=30, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    check_in = models.CharField(max_length=10, default="14:00")
    check_out = models.CharField(max_length=10, default="12:00")
    policies = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=STATES, default="pending", db_index=True)
    review_note = models.CharField(max_length=300, blank=True, default="")
    featured = models.BooleanField(default=False)
    rating = models.FloatField(default=0)
    reviews = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Room(models.Model):
    prop = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=80)
    adults = models.PositiveSmallIntegerField(default=2)
    beds = models.CharField(max_length=80, blank=True, default="")
    price = models.PositiveIntegerField()                               # per night, PKR
    count = models.PositiveSmallIntegerField(default=1)                 # how many rooms of this type
    about = models.CharField(max_length=300, blank=True, default="")
    amenities = models.JSONField(default=list, blank=True)
    photos = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]


class Block(models.Model):
    """Rooms closed by the owner (repairs, or booked by phone / walk-in) for some nights."""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="blocks")
    start = models.DateField()
    end = models.DateField()                                            # check-out style: the night of `end` is free again
    count = models.PositiveSmallIntegerField(default=1)
    note = models.CharField(max_length=120, blank=True, default="")


class Tour(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="tours")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tours")
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=90, unique=True)
    destination = models.CharField(max_length=80, db_index=True)        # e.g. Hunza, Skardu, Umrah
    start_city = models.CharField(max_length=60, blank=True, default="")
    country = models.CharField(max_length=2, default="PK")
    days = models.PositiveSmallIntegerField(default=3)
    nights = models.PositiveSmallIntegerField(default=2)
    price = models.PositiveIntegerField()                               # per person, PKR
    child_price = models.PositiveIntegerField(default=0)
    includes = models.JSONField(default=list, blank=True)
    excludes = models.JSONField(default=list, blank=True)
    itinerary = models.JSONField(default=list, blank=True)              # [{"t": "Day title", "x": "what happens"}]
    departures = models.JSONField(default=list, blank=True)             # [{"d": "2026-11-05", "seats": 20}]; empty = any date on request
    max_group = models.PositiveSmallIntegerField(default=20)
    about = models.TextField(blank=True, default="")
    photos = models.JSONField(default=list, blank=True)
    phone = models.CharField(max_length=30, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATES, default="pending", db_index=True)
    review_note = models.CharField(max_length=300, blank=True, default="")
    featured = models.BooleanField(default=False)
    rating = models.FloatField(default=0)
    reviews = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Booking(models.Model):
    STATUS = [("pending", "Waiting for the owner"), ("confirmed", "Confirmed"), ("declined", "Declined"), ("cancelled", "Cancelled"),
              ("checked_in", "Checked in"), ("done", "Completed"), ("no_show", "Did not come")]
    code = models.CharField(max_length=10, unique=True)
    kind = models.CharField(max_length=5)                               # room | tour
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.CASCADE, related_name="bookings")
    tour = models.ForeignKey(Tour, null=True, blank=True, on_delete=models.CASCADE, related_name="bookings")
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trip_bookings")
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=30)
    start = models.DateField()                                          # check-in / tour date
    end = models.DateField(null=True, blank=True)                       # check-out
    qty = models.PositiveSmallIntegerField(default=1)                   # rooms, or people (adults)
    children = models.PositiveSmallIntegerField(default=0)
    guests = models.PositiveSmallIntegerField(default=1)
    total = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=300, blank=True, default="")
    owner_note = models.CharField(max_length=300, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Review(models.Model):
    """Only from a guest whose booking was completed - no other way to leave one."""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    stars = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=600, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
