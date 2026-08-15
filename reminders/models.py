from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

MONTHS = [(1,"January"),(2,"February"),(3,"March"),(4,"April"),(5,"May"),(6,"June"),
          (7,"July"),(8,"August"),(9,"September"),(10,"October"),(11,"November"),(12,"December")]

RELATIONS = [
    ("family", "Family"), ("parent", "Parent"), ("sibling", "Brother or sister"),
    ("child", "Son or daughter"), ("spouse", "Husband or wife"),
    ("friend", "Friend"), ("colleague", "Colleague"), ("other", "Other"),
]

DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


class Birthday(models.Model):
    """
    Someone else's birthday, saved by one of our users.

    This is another person's personal data, held by a third party who never
    agreed to anything here. Three things follow from that, and they are the
    reason the model looks like this:

      * The year is optional. A birthday needs a day and a month; an age is
        extra information nobody has to hand over.
      * Contact details are optional and are never used to message that
        person. They sit here so the owner can reach them - nothing more.
      * Everything a user saves goes when their account goes.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="birthdays")
    name = models.CharField(max_length=120)
    relation = models.CharField(max_length=20, choices=RELATIONS, default="friend")

    day = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField(choices=MONTHS)
    year = models.PositiveSmallIntegerField(null=True, blank=True)

    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    note = models.CharField(max_length=300, blank=True, default="")

    days_before = models.PositiveSmallIntegerField(default=3)
    remind_on_day = models.BooleanField(default=True)

    # Guards against a cron that runs twice, or a server that reboots mid-run:
    # a reminder for a given year is sent once and only once.
    last_advance_year = models.PositiveSmallIntegerField(null=True, blank=True)
    last_dayof_year = models.PositiveSmallIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["month", "day", "name"]
        indexes = [models.Index(fields=["month", "day"])]

    def __str__(self):
        return "%s (%02d/%02d)" % (self.name, self.day, self.month)

    def clean_date(self):
        m = max(1, min(12, int(self.month)))
        d = max(1, min(DAYS_IN_MONTH[m - 1], int(self.day)))
        self.month, self.day = m, d

    def save(self, *args, **kwargs):
        self.clean_date()
        super().save(*args, **kwargs)

    def occurrence(self, in_year):
        """
        This birthday's date in a given year.

        29 February falls back to the 28th in ordinary years. Skipping it
        instead would mean those people never get remembered at all in three
        years out of four.
        """
        d = self.day
        if self.month == 2 and d == 29:
            leap = (in_year % 4 == 0 and in_year % 100 != 0) or in_year % 400 == 0
            if not leap:
                d = 28
        return date(in_year, self.month, d)

    def next_occurrence(self, today=None):
        today = today or timezone.localdate()
        this = self.occurrence(today.year)
        return this if this >= today else self.occurrence(today.year + 1)

    @property
    def days_away(self):
        return (self.next_occurrence() - timezone.localdate()).days

    @property
    def turning(self):
        """Age on the next birthday, or None when no year was given."""
        if not self.year:
            return None
        return self.next_occurrence().year - self.year

    @property
    def pretty(self):
        return "%d %s" % (self.day, MONTHS[self.month - 1][1])


class Sent(models.Model):
    """A log of what went out, so a duplicate can be traced rather than argued about."""

    ADVANCE, DAY_OF = "advance", "day_of"
    KINDS = [(ADVANCE, "Days before"), (DAY_OF, "On the day")]

    birthday = models.ForeignKey(Birthday, on_delete=models.CASCADE, related_name="sent")
    kind = models.CharField(max_length=10, choices=KINDS)
    for_year = models.PositiveSmallIntegerField()
    sent_at = models.DateTimeField(default=timezone.now)
    ok = models.BooleanField(default=True)

    class Meta:
        ordering = ["-sent_at"]
        unique_together = [("birthday", "kind", "for_year")]
