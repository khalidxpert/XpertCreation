"""Every 5 minutes (cron): turn what members did into points, within the daily caps.
Looks back 2 days, never counts the same thing twice, and takes points back for posts,
comments and reactions that were hidden by a moderator or deleted."""
from datetime import timedelta

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.models import Count, F
from django.utils import timezone

from rewards.models import DailyActivity, PointEvent
from rewards.views import REVOKE, SOURCES, TIME_CAP, TIME_POINTS, TIME_STEP, campaign, live


class Command(BaseCommand):
    help = "Collect rewards points from members' activity (posts, lessons, MCQs, games, typing, active time)."

    def handle(self, *args, **kwargs):
        c = campaign()
        now = timezone.now()
        since = now - timedelta(days=2)
        staff_only = not live(c)
        if not staff_only:
            since = max(since, c.starts_at)
        first_day = timezone.localtime(since).date()
        added = removed = 0

        for kind, (model, uf, tf, flt, pts, cap, _sec) in SOURCES.items():
            M = apps.get_model(model)
            qs = M.objects.filter(**{tf + "__gte": since}).filter(**flt)
            rel = uf[:-3]                                    # author_id -> author
            qs = qs.filter(**{rel + "__is_active": True, rel + "__is_blocked": False})
            if staff_only:
                qs = qs.filter(**{rel + "__is_staff": True})
            if kind == "reaction":
                qs = qs.exclude(post__author_id=F("user_id"))   # no points for reacting to your own post
            if kind in REVOKE:
                # an event loses its points when its row was deleted, or is inside the window but no longer
                # passes the filters (hidden by a moderator, author blocked); older rows are left alone
                cand = PointEvent.objects.filter(kind=kind, day__gte=first_day)
                if staff_only:
                    cand = cand.filter(user__is_staff=True)
                ok = set(str(i) for i in qs.values_list("id", flat=True))
                cand = [(e.pk, e.ref) for e in cand.only("pk", "ref") if e.ref not in ok]
                if cand:
                    ids = [int(r) for _, r in cand if r.isdigit()]
                    when = dict(M.objects.filter(id__in=ids).values_list("id", tf))
                    gone = [pk for pk, r in cand if r.isdigit() and (int(r) not in when or (when[int(r)] and when[int(r)] >= since))]
                    if gone:
                        removed += PointEvent.objects.filter(pk__in=gone).delete()[0]

            rows = list(qs.order_by(tf).values_list("id", uf, tf)[:20000])
            ev = PointEvent.objects.filter(kind=kind, day__gte=first_day)
            have = set(ev.values_list("ref", flat=True))
            used = {(r["user_id"], r["day"]): r["n"] for r in ev.values("user_id", "day").annotate(n=Count("id"))}
            for oid, uid, t in rows:
                ref = str(oid)
                if ref in have or uid is None or t is None:
                    continue
                day = timezone.localtime(t).date()
                if used.get((uid, day), 0) >= cap:
                    continue
                _, made = PointEvent.objects.get_or_create(user_id=uid, kind=kind, ref=ref, defaults={"day": day, "points": pts})
                if made:
                    used[(uid, day)] = used.get((uid, day), 0) + 1
                    added += 1

        acts = DailyActivity.objects.filter(day__gte=first_day)
        if staff_only:
            acts = acts.filter(user__is_staff=True)
        for a in acts:
            p = min(TIME_CAP, (a.active_seconds // TIME_STEP) * TIME_POINTS)
            if p <= 0:
                continue
            e, made = PointEvent.objects.get_or_create(user_id=a.user_id, kind="time", ref=a.day.isoformat(),
                                                       defaults={"day": a.day, "points": p})
            if made:
                added += 1
            elif e.points != p:
                PointEvent.objects.filter(pk=e.pk).update(points=p)

        if added or removed:
            self.stdout.write("%s rewards_collect: %s, +%d events, -%d revoked"
                              % (now.isoformat(timespec="seconds"), "live" if not staff_only else "staff only", added, removed))

        # stage 4: referrals, commissions on real payments, referral draws
        from rewards.views import qualify_referrals, run_commissions, run_draws
        q = qualify_referrals()
        made, rel, rev = run_commissions()
        dr = run_draws(c) if not staff_only or (c.enabled and c.starts_at and now >= c.starts_at) else []
        if q or made or rel or rev or dr:
            self.stdout.write("%s referrals: %d qualified; commissions +%d new, %d released, %d reversed; draws run: %s"
                              % (now.isoformat(timespec="seconds"), q, made, rel, rev, dr or "-"))
