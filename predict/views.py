"""Cricket predictions: pick the winner before the start; 10 points for a right pick; monthly and all-time leaderboards."""
from datetime import datetime, timedelta

from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Match, Pick

POINTS = 10


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _out(m, mine):
    c = dict(m.picks.values_list("pick").annotate(n=Count("id")))
    tot = sum(c.values()) or 1
    return {"id": m.id, "a": m.team_a, "b": m.team_b, "series": m.series, "starts": m.starts_at.isoformat(), "open": m.starts_at > timezone.now() and not m.result,
            "result": m.result, "mine": mine.get(m.id, ""), "votes": sum(c.values()),
            "pct": {k: round(100 * c.get(k, 0) / tot) for k in ("a", "b", "draw")}}


def _board(since=None):
    qs = Pick.objects.filter(match__result__in=["a", "b", "draw"]).filter(pick=F("match__result"))
    if since:
        qs = qs.filter(match__starts_at__gte=since)
    rows = list(qs.values("user_id").annotate(n=Count("id")).order_by("-n")[:20])
    from django.contrib.auth import get_user_model
    us = {u.pk: u for u in get_user_model().objects.filter(pk__in=[r["user_id"] for r in rows])}
    nm = lambda u: ((getattr(u, "full_name", "") or "").strip() or getattr(u, "username", "") or "Member") if u else "Member"
    return [{"name": nm(us.get(r["user_id"])), "points": r["n"] * POINTS} for r in rows]


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def matches(request):
    u = request.user
    if request.method == "GET":
        now = timezone.now()
        up = list(Match.objects.filter(result="", starts_at__gte=now - timedelta(hours=10)).order_by("starts_at")[:30])
        done = list(Match.objects.exclude(result="").order_by("-starts_at")[:15])
        mine = dict(Pick.objects.filter(user=u, match__in=up + done).values_list("match_id", "pick")) if u.is_authenticated else {}
        first = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        out = {"upcoming": [_out(m, mine) for m in up], "results": [_out(m, mine) for m in done], "month": _board(first), "all": _board(), "staff": _staff(u)}
        if u.is_authenticated:
            right = Pick.objects.filter(user=u, pick=F("match__result")).count()
            out["me"] = {"points": right * POINTS, "picks": Pick.objects.filter(user=u).count()}
        return Response(out)
    if not _staff(u):
        return Response({"detail": "Only staff can add matches."}, status=403)
    d = request.data
    a, b = str(d.get("a") or "").strip()[:40], str(d.get("b") or "").strip()[:40]
    try:
        st = timezone.make_aware(datetime.strptime(str(d.get("starts")), "%Y-%m-%dT%H:%M")) if timezone.is_naive(datetime.strptime(str(d.get("starts")), "%Y-%m-%dT%H:%M")) else None
    except (ValueError, TypeError):
        return Response({"detail": "Start time should look like 2026-10-12T14:00."}, status=400)
    if not a or not b or a.lower() == b.lower():
        return Response({"detail": "Add two different teams."}, status=400)
    m = Match.objects.create(team_a=a, team_b=b, series=str(d.get("series") or "")[:80], starts_at=st)
    return Response({"id": m.id}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pick(request, pk):
    m = Match.objects.filter(pk=pk).first()
    if not m:
        return Response({"detail": "Match not found."}, status=404)
    p = str(request.data.get("pick") or "")
    if p not in ("a", "b", "draw"):
        return Response({"detail": "Pick a team."}, status=400)
    if m.result or m.starts_at <= timezone.now():
        return Response({"detail": "Predictions closed when the match started."}, status=400)
    Pick.objects.update_or_create(match=m, user=request.user, defaults={"pick": p})
    return Response({"pick": p})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def settle(request, pk):
    if not _staff(request.user):
        return Response({"detail": "Only staff can do that."}, status=403)
    m = Match.objects.filter(pk=pk).first()
    if not m:
        return Response({"detail": "Match not found."}, status=404)
    if request.method == "DELETE":
        m.delete(); return Response({"deleted": True})
    r = str(request.data.get("result") or "")
    if r not in ("a", "b", "draw", "nr"):
        return Response({"detail": "Result must be a, b, draw or nr."}, status=400)
    m.result = r; m.save(update_fields=["result"])
    return Response({"result": r, "winners": m.picks.filter(pick=r).count() if r != "nr" else 0})
