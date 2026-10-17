"""Food delivery: restaurants, home kitchens, bakeries... with a menu; buyers order for delivery or pickup and
follow the order live (placed -> accepted -> on the way -> delivered). The restaurant delivers with its own rider."""
from django.conf import settings
from django.db import models

KINDS = [("restaurant", "Restaurant"), ("fastfood", "Fast food"), ("bbq", "BBQ & karahi"), ("fish", "Fish"), ("chinese", "Chinese"),
         ("pizza", "Pizza"), ("bakery", "Bakery & cakes"), ("sweets", "Sweets"), ("cafe", "Cafe & drinks"), ("home", "Home kitchen"),
         ("dhaba", "Dhaba & desi"), ("other", "Other")]


class Restaurant(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="restaurant")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    kind = models.CharField(max_length=12, choices=KINDS, default="restaurant", db_index=True)
    cuisines = models.CharField(max_length=160, blank=True, default="")      # "Burgers, Fried chicken, Shakes"
    city = models.CharField(max_length=60, db_index=True)
    area = models.CharField(max_length=80, blank=True, default="")
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    about = models.TextField(max_length=1000, blank=True, default="")
    logo = models.CharField(max_length=200, blank=True, default="")
    cover = models.CharField(max_length=200, blank=True, default="")
    delivers = models.BooleanField(default=True)
    pickup = models.BooleanField(default=True)
    areas = models.TextField(max_length=2000, blank=True, default="")         # areas it delivers to, comma separated; empty = whole city
    min_order = models.PositiveIntegerField(default=0)
    delivery_fee = models.PositiveIntegerField(default=0)
    free_over = models.PositiveIntegerField(default=0)                       # free delivery above this (0 = never)
    eta_min = models.PositiveSmallIntegerField(default=30)
    eta_max = models.PositiveSmallIntegerField(default=45)
    hours = models.JSONField(default=dict, blank=True)                       # {"mon": ["12:00", "23:30"] or None, ...}
    paused = models.BooleanField(default=False)                              # "busy - not taking orders now"
    status = models.CharField(max_length=10, default="pending", db_index=True)   # pending | approved | rejected | suspended
    note = models.CharField(max_length=300, blank=True, default="")
    rating_sum = models.PositiveIntegerField(default=0)
    rating_n = models.PositiveIntegerField(default=0)
    orders_done = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Section(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=60)
    pos = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["pos", "id"]


class Item(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="items")
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    name = models.CharField(max_length=100)
    desc = models.CharField(max_length=300, blank=True, default="")
    price = models.PositiveIntegerField()
    old_price = models.PositiveIntegerField(default=0)
    image = models.CharField(max_length=200, blank=True, default="")
    # [{"name": "Size", "need": true, "multi": false, "choices": [{"name": "Regular", "price": 0}, {"name": "Large", "price": 150}]}]
    options = models.JSONField(default=list, blank=True)
    available = models.BooleanField(default=True)
    popular = models.BooleanField(default=False)
    sold = models.PositiveIntegerField(default=0)
    pos = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["pos", "id"]


class FoodOrder(models.Model):
    """placed -> accepted -> on_way (delivery) / ready (pickup) -> delivered. Side roads: rejected, cancelled."""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="food_orders")
    items = models.JSONField(default=list)            # [{"id", "name", "qty", "price" (one, with options), "opts": "Large, Extra cheese"}]
    subtotal = models.PositiveIntegerField()
    delivery = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField()
    fee = models.PositiveIntegerField(default=0)      # XpertCreation's commission (see COMMISSION_PCT)
    payment = models.CharField(max_length=6, default="cod")
    mode = models.CharField(max_length=8, default="delivery")      # delivery | pickup
    status = models.CharField(max_length=10, default="placed", db_index=True)
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=300, blank=True, default="")
    area = models.CharField(max_length=80, blank=True, default="")
    city = models.CharField(max_length=60, blank=True, default="")
    note = models.CharField(max_length=300, blank=True, default="")
    prep_min = models.PositiveSmallIntegerField(default=0)         # minutes the restaurant said when accepting
    rider = models.CharField(max_length=80, blank=True, default="")
    reason = models.CharField(max_length=200, blank=True, default="")
    rating = models.PositiveSmallIntegerField(default=0)
    review = models.CharField(max_length=500, blank=True, default="")
    reply = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    out_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
