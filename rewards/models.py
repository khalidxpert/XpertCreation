"""Rewards campaign: points for real use of the site. Stage 1 = points and leaderboard.
The wheel, scratch cards, referrals and payouts come in later stages."""
from django.conf import settings
from django.db import models


class Campaign(models.Model):
    """One row. Off until switched on with: manage.py rewards_campaign on --start YYYY-MM-DD --days 30.
    While off (or after it ends) only staff accounts earn points, so it can be tested."""
    enabled = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    budget = models.PositiveIntegerField(default=10000)          # rupees, used by the prize stages
    youtube_url = models.CharField(max_length=200, blank=True, default="https://www.youtube.com/@XpertCreationPK?sub_confirmation=1")
    facebook_url = models.CharField(max_length=200, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)


class PointEvent(models.Model):
    """One reason a member got points (a post, a lesson, 10 minutes of activity...).
    ref names the thing, so the same post or lesson is never counted twice."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    day = models.DateField(db_index=True)
    kind = models.CharField(max_length=12)
    ref = models.CharField(max_length=100)
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "kind", "ref")]
        indexes = [models.Index(fields=["day", "user"]), models.Index(fields=["kind", "day"])]


class DailyActivity(models.Model):
    """Active seconds per member per day: the tab was visible and used in the last minute."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    day = models.DateField(db_index=True)
    active_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "day")]


class PrizeSlot(models.Model):
    """One prize with its secret release time (stage 2). The first eligible spin after release_at wins it;
    if nobody spins, it waits for the next spin, so every prize in the schedule is really given."""
    kind = models.CharField(max_length=10, default="wheel")
    amount = models.PositiveIntegerField()
    release_at = models.DateTimeField(db_index=True)
    won_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    won_at = models.DateTimeField(null=True, blank=True)


class Spin(models.Model):
    """One wheel spin. kind: daily (30 points today) or explorer (5 sections today)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    day = models.DateField(db_index=True)
    kind = models.CharField(max_length=10)
    test = models.BooleanField(default=False)
    amount = models.PositiveIntegerField(default=0)
    slot = models.ForeignKey(PrizeSlot, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "day", "kind")]


class RewardEntry(models.Model):
    """The rewards balance, one line per change: + for prizes, - for withdrawals or spending (stage 3)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    amount = models.IntegerField()
    kind = models.CharField(max_length=10)            # win | scratch | draw | withdraw | spend | adjust
    note = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class RewardSteps(models.Model):
    """The steps a member finishes once before withdrawing (stage 3): an XpertConnect post about the
    rewards, a post in IRC #xpertcreation (checked by XpertBot with the code), YouTube and Facebook."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    code = models.CharField(max_length=12, unique=True)
    post_id = models.PositiveIntegerField(null=True, blank=True)
    post_at = models.DateTimeField(null=True, blank=True)
    irc_at = models.DateTimeField(null=True, blank=True)
    youtube_at = models.DateTimeField(null=True, blank=True)
    facebook_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Withdrawal(models.Model):
    """A request to be paid from the rewards balance. The amount leaves the balance when requested
    and comes back if the request is rejected or cancelled."""
    METHODS = [("easypaisa", "EasyPaisa"), ("jazzcash", "JazzCash"), ("bank", "Bank transfer"),
               ("load", "Mobile load"), ("other", "Other (arrange with admin)")]
    STATES = [("requested", "Waiting"), ("paid", "Paid"), ("rejected", "Rejected"), ("cancelled", "Cancelled")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    amount = models.PositiveIntegerField()
    method = models.CharField(max_length=10, choices=METHODS)
    country = models.CharField(max_length=2, default="PK")
    account_name = models.CharField(max_length=80, blank=True, default="")
    account_no = models.CharField(max_length=40, blank=True, default="")
    account_key = models.CharField(max_length=40, blank=True, default="", db_index=True)   # digits only, for the one-account rule
    bank_name = models.CharField(max_length=80, blank=True, default="")
    network = models.CharField(max_length=20, blank=True, default="")
    details = models.TextField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATES, default="requested", db_index=True)
    admin_note = models.CharField(max_length=300, blank=True, default="")
    proof_path = models.CharField(max_length=200, blank=True, default="")
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
