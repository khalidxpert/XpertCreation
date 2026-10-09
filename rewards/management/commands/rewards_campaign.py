"""Switch the rewards campaign on or off, or see its state.
  manage.py rewards_campaign status
  manage.py rewards_campaign on --start 2026-10-15 --days 30
  manage.py rewards_campaign off
  manage.py rewards_campaign links --youtube URL --facebook URL   (claim-step links; empty hides a step)"""
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum
from django.utils import timezone

from rewards.models import DailyActivity, PointEvent
from rewards.models import PrizeSlot
from rewards.views import campaign, given_total, live, make_slots


class Command(BaseCommand):
    help = "Rewards campaign: status | on --start YYYY-MM-DD --days N | off"

    def add_arguments(self, p):
        p.add_argument("action", choices=["status", "on", "off", "links"])
        p.add_argument("--youtube")
        p.add_argument("--facebook")
        p.add_argument("--start", help="first day, YYYY-MM-DD (Pakistan time); default today")
        p.add_argument("--days", type=int, default=30)

    def handle(self, *args, **o):
        c = campaign()
        if o["action"] == "on":
            try:
                d = datetime.strptime(o["start"], "%Y-%m-%d").date() if o["start"] else timezone.localdate()
            except ValueError:
                raise CommandError("--start must look like 2026-10-15")
            if not 1 <= o["days"] <= 365:
                raise CommandError("--days must be 1 to 365")
            c.starts_at = timezone.make_aware(datetime.combine(d, time.min))
            c.ends_at = c.starts_at + timedelta(days=o["days"])
            c.enabled = True
            c.save()
            self.stdout.write("wheel prizes scheduled: %d (secret times, one a day)" % make_slots(c))
        elif o["action"] == "links":
            for k in ("youtube", "facebook"):
                v = o[k]
                if v is not None:
                    if v and not v.startswith("https://"):
                        raise CommandError("--%s must start with https://" % k)
                    setattr(c, k + "_url", v[:200])
            c.save()
            self.stdout.write("youtube: %s\nfacebook: %s" % (c.youtube_url or "(step hidden)", c.facebook_url or "(step hidden)"))
        elif o["action"] == "off":
            c.enabled = False
            c.save()
        fmt = lambda t: timezone.localtime(t).strftime("%d %b %Y %H:%M") if t else "-"
        self.stdout.write("campaign: %s (enabled=%s)  from %s  until %s  budget Rs %s"
                          % ("LIVE" if live(c) else "not live", c.enabled, fmt(c.starts_at), fmt(c.ends_at), c.budget))
        ev = PointEvent.objects.all()
        if c.starts_at:
            ev = ev.filter(day__gte=timezone.localtime(c.starts_at).date())
        a = ev.aggregate(p=Sum("points"), u=Count("user", distinct=True))
        self.stdout.write("points so far: %s by %s members; active-time rows: %s"
                          % (a["p"] or 0, a["u"] or 0, DailyActivity.objects.count()))
        ps = PrizeSlot.objects.filter(kind="wheel")
        self.stdout.write("wheel prizes: %d scheduled, %d won, %d waiting now; given so far Rs %d of Rs %d"
                          % (ps.count(), ps.filter(won_by__isnull=False).count(),
                             ps.filter(won_by__isnull=True, release_at__lte=timezone.now()).count(), given_total(), c.budget))
        for r in ev.values("kind").annotate(p=Sum("points"), n=Count("id")).order_by("-p"):
            self.stdout.write("  %-9s %6d points from %5d events" % (r["kind"], r["p"], r["n"]))
