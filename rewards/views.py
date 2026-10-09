"""Rewards stage 1: points for real use of every part of the site, and a transparent leaderboard.

Points are counted from what members already do (posts, lessons, MCQs, games, typing) by the
rewards_collect job every 5 minutes, plus a small heartbeat from the page for active time, tools and reading.
Every rule has a daily cap so nobody can farm points."""
from datetime import timedelta

from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Campaign, DailyActivity, PointEvent

# kind: (app.Model, user field, time field, filters, points, max per day, section)
SOURCES = {
    "post":     ("feed.Post", "author_id", "created_at", {"hidden": False}, 5, 2, "social"),
    "comment":  ("feed.Comment", "author_id", "created_at", {"hidden": False}, 1, 5, "social"),
    "reaction": ("feed.Reaction", "user_id", "created_at", {}, 1, 5, "social"),
    "lesson":   ("academy.LessonProgress", "user_id", "completed_at", {}, 5, 6, "academy"),
    "quiz":     ("academy.Attempt", "user_id", "submitted_at", {"passed": True}, 10, 2, "academy"),
    "mcq":      ("mcq.Attempt", "user_id", "created_at", {}, 5, 1, "mcq"),
    "game":     ("games.Score", "user_id", "created_at", {}, 2, 5, "games"),
    "typing":   ("typingtutor.Score", "user_id", "created_at", {}, 2, 5, "typing"),
}
REVOKE = ("post", "comment", "reaction")       # points go away if the post is hidden or deleted
BEAT_KINDS = {"tool": (1, 5, "tools"), "read": (2, 3, "reading")}   # points, max per day, section
TIME_STEP, TIME_POINTS, TIME_CAP = 600, 2, 12  # 2 points per 10 active minutes, up to 12 a day
MAX_ACTIVE = 4 * 3600                          # active time stops counting after 4 hours a day
BEAT_EVERY = 60
SECTION = dict({k: v[6] for k, v in SOURCES.items()}, tool="tools", read="reading", time="time")


def campaign():
    c = Campaign.objects.first()
    return c or Campaign.objects.create()


def live(c=None):
    c = c or campaign()
    now = timezone.now()
    return bool(c.enabled and c.starts_at and c.ends_at and c.starts_at <= now < c.ends_at)


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def counts_for(u, c=None):
    """Live campaign: every active member. Otherwise only staff (for testing)."""
    if not u or not u.is_authenticated or getattr(u, "is_blocked", False):
        return False
    return live(c) or _staff(u)


def award(user_id, day, kind, ref, points, cap):
    """Add one point event unless it is already there or the daily cap for this kind is reached."""
    if PointEvent.objects.filter(user_id=user_id, day=day, kind=kind).count() >= cap:
        return False
    try:
        _, made = PointEvent.objects.get_or_create(user_id=user_id, kind=kind, ref=ref[:100],
                                                   defaults={"day": day, "points": points})
        return made
    except IntegrityError:
        return False


def _status(c):
    return {"on": live(c), "enabled": c.enabled, "budget": c.budget,
            "starts": c.starts_at.isoformat() if c.starts_at else "", "ends": c.ends_at.isoformat() if c.ends_at else ""}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def beat(request):
    """Sent by the page once a minute while the tab is visible and used. Adds active time,
    and points for using a tool or reading (s = "tool:<name>" or "read:<path>")."""
    u, c = request.user, campaign()
    if not counts_for(u, c):
        return Response({"on": False}, status=404)
    if not cache.add("rw:beat:%d" % u.pk, 1, BEAT_EVERY - 5):
        return Response({"ok": False, "why": "too soon"})
    day = timezone.localdate()
    row, _ = DailyActivity.objects.get_or_create(user=u, day=day)
    if row.active_seconds < MAX_ACTIVE:
        DailyActivity.objects.filter(pk=row.pk).update(active_seconds=F("active_seconds") + BEAT_EVERY)
    s = str(request.data.get("s") or "").strip()[:80]
    kind = s.split(":", 1)[0]
    if kind in BEAT_KINDS and len(s) > len(kind) + 1:
        pts, cap, _sec = BEAT_KINDS[kind]
        award(u.pk, day, kind, "%s|%s" % (s, day.isoformat()), pts, cap)
    return Response({"ok": True})


def _label(u):
    if getattr(u, "hide_from_leaderboard", False) or not u.username:
        return "Member #%d" % u.pk
    return "@" + u.username


@api_view(["GET"])
@permission_classes([AllowAny])
def board(request):
    """Leaderboard: everyone's points and active time. period = today | all."""
    from django.contrib.auth import get_user_model
    c = campaign()
    out = _status(c)
    if not live(c) and not _staff(request.user):
        return Response(dict(out, rows=[]))
    today = request.GET.get("period") == "today"
    ev = PointEvent.objects.filter(user__is_active=True, user__is_blocked=False)
    act = DailyActivity.objects.all()
    if today:
        d = timezone.localdate()
        ev, act = ev.filter(day=d), act.filter(day=d)
    elif c.starts_at:
        ev, act = ev.filter(day__gte=timezone.localtime(c.starts_at).date()), act.filter(day__gte=timezone.localtime(c.starts_at).date())
    top = list(ev.values("user_id").annotate(p=Sum("points")).order_by("-p", "user_id")[:100])
    ids = [r["user_id"] for r in top]
    users = {u.pk: u for u in get_user_model().objects.filter(pk__in=ids)}
    mins = dict(act.filter(user_id__in=ids).values_list("user_id").annotate(s=Sum("active_seconds")))
    rows = []
    for i, r in enumerate(top, 1):
        u = users.get(r["user_id"])
        if u:
            rows.append({"rank": i, "name": _label(u), "points": r["p"], "minutes": (mins.get(u.pk) or 0) // 60,
                         "spins": 0, "referrals": 0, "me": request.user.is_authenticated and u.pk == request.user.pk})
    return Response(dict(out, period="today" if today else "all", rows=rows))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """My points today and in total, my active minutes and which sections I used today."""
    u, c, d = request.user, campaign(), timezone.localdate()
    mine = PointEvent.objects.filter(user=u)
    if c.starts_at:
        mine = mine.filter(day__gte=timezone.localtime(c.starts_at).date())
    t = mine.filter(day=d)
    by_kind = dict(t.values_list("kind").annotate(p=Sum("points")))
    act = DailyActivity.objects.filter(user=u, day=d).first()
    return Response(dict(_status(c), counting=counts_for(u, c), today=sum(by_kind.values()), total=mine.aggregate(p=Sum("points"))["p"] or 0,
                         by_kind=by_kind, sections=sorted({SECTION.get(k, k) for k in by_kind} - {"time"}),
                         minutes_today=(act.active_seconds if act else 0) // 60))
