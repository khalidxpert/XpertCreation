"""Freelance marketplace: gigs (fixed-price services) and projects (buyers post, freelancers bid).
Buyers pay XpertCreation through Safepay; the seller's share (90%) is added to their balance when the order is
completed, and sellers withdraw to EasyPaisa, JazzCash or a bank (paid by hand by the team)."""
from django.conf import settings
from django.db import models

CATS = [("design", "Design"), ("writing", "Writing & translation"), ("web", "Websites & apps"), ("marketing", "Digital marketing"),
        ("video", "Video & animation"), ("office", "Office, data & Excel"), ("teaching", "Teaching & tutoring"),
        ("business", "Business & accounts"), ("other", "Other")]


class Gig(models.Model):
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gigs")
    title = models.CharField(max_length=100)
    category = models.CharField(max_length=12, choices=CATS, default="other", db_index=True)
    description = models.TextField(max_length=4000)
    price = models.PositiveIntegerField()                       # rupees
    days = models.PositiveSmallIntegerField(default=3)          # delivery time
    revisions = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True, db_index=True)
    hidden = models.BooleanField(default=False, db_index=True)  # hidden by a moderator
    orders_done = models.PositiveIntegerField(default=0)
    rating_sum = models.PositiveIntegerField(default=0)
    rating_n = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]


class Project(models.Model):
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="market_projects")
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=12, choices=CATS, default="other", db_index=True)
    description = models.TextField(max_length=4000)
    budget = models.PositiveIntegerField()                      # rupees, the most the buyer wants to pay
    days = models.PositiveSmallIntegerField(default=7)
    status = models.CharField(max_length=10, default="open", db_index=True)   # open | assigned | closed
    hidden = models.BooleanField(default=False, db_index=True)
    bids_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-id"]


class Bid(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="bids")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="market_bids")
    amount = models.PositiveIntegerField()
    days = models.PositiveSmallIntegerField()
    note = models.TextField(max_length=1500)
    status = models.CharField(max_length=10, default="sent")    # sent | accepted | rejected | withdrawn
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("project", "seller")]
        ordering = ["amount", "id"]


class Order(models.Model):
    """pending (not paid) -> active (paid, seller working) -> delivered -> completed.
    Side roads: cancelled (never paid), disputed (team decides), refund_due -> refunded (team sends the money back)."""
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="market_buys")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="market_sales")
    gig = models.ForeignKey(Gig, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")
    bid = models.OneToOneField(Bid, null=True, blank=True, on_delete=models.SET_NULL, related_name="order")
    title = models.CharField(max_length=120)
    amount = models.PositiveIntegerField()                      # what the buyer pays, rupees
    fee = models.PositiveIntegerField()                         # XpertCreation's share (10%)
    days = models.PositiveSmallIntegerField()
    revisions_left = models.PositiveSmallIntegerField(default=1)
    requirements = models.TextField(max_length=3000, blank=True, default="")
    status = models.CharField(max_length=12, default="pending", db_index=True)
    provider = models.CharField(max_length=20, blank=True, default="")
    provider_ref = models.CharField(max_length=120, blank=True, default="", db_index=True)
    delivery = models.TextField(max_length=3000, blank=True, default="")
    note = models.CharField(max_length=300, blank=True, default="")      # dispute reason / team note
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]


class Message(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")  # null = the system
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class Entry(models.Model):
    """The seller's balance is the sum of their entries: + earnings, - withdrawals (+ back if a withdrawal is rejected)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="market_entries")
    amount = models.IntegerField()
    kind = models.CharField(max_length=12)                      # earning | payout | payout_back | adjust
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["order", "kind"], name="market_entry_once", condition=models.Q(kind="earning"))]


class Payout(models.Model):
    METHODS = [("easypaisa", "EasyPaisa"), ("jazzcash", "JazzCash"), ("bank", "Bank account")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="market_payouts")
    amount = models.PositiveIntegerField()
    method = models.CharField(max_length=10, choices=METHODS)
    account_name = models.CharField(max_length=80)
    account_no = models.CharField(max_length=40)
    bank = models.CharField(max_length=80, blank=True, default="")
    status = models.CharField(max_length=10, default="requested", db_index=True)   # requested | paid | rejected
    reference = models.CharField(max_length=120, blank=True, default="")          # transaction id from the team
    note = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
