"""Step counter: members' walks, runs and rides (steps, distance, time, route) and their daily goal.
Counting happens on the phone; this only keeps the results so they survive a new phone or a cleared browser."""
from datetime import date, datetime, timedelta

from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Prefs, Walk

KINDS = ("walk", "run", "cycle")


def _int(v, lo, hi):
    try:
        v = int(float(v))
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def _row(w, with_path=False):
    d = {"id": w.id, "kind": w.kind, "started_at": w.started_at.isoformat(), "day": w.day.isoformat(), "secs": w.secs,
         "steps": w.steps, "steps_est": w.steps_est, "dist_m": w.dist_m, "kcal": w.kcal, "points": len(w.path or [])}
    if with_path:
        d["path"] = w.path
    return d


def _prefs(u):
    p, _ = Prefs.objects.get_or_create(user=u)
    return {"goal": p.goal, "height_cm": p.height_cm, "weight_kg": p.weight_kg}


def _clean_path(p):
    if not isinstance(p, list):
        return None
    out = []
    for pt in p[:6000]:
        try:
            la, ln = round(float(pt[0]), 5), round(float(pt[1]), 5)
        except (TypeError, ValueError, IndexError, KeyError):
            return None
        if not (-90 <= la <= 90 and -180 <= ln <= 180):
            return None
        out.append([la, ln])
    return out


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def walks(request):
    u = request.user
    if request.method == "GET":
        days = _int(request.GET.get("days", 30), 1, 400) or 30
        today = _day(request.GET.get("today")) or date.today()
        since = today - timedelta(days=days - 1)
        qs = Walk.objects.filter(user=u, day__gte=since)
        totals = {}
        for r in qs.values("day").annotate(steps=Sum("steps"), dist_m=Sum("dist_m"), kcal=Sum("kcal"), secs=Sum("secs")):
            totals[r["day"].isoformat()] = {"steps": r["steps"], "dist_m": r["dist_m"], "kcal": r["kcal"], "secs": r["secs"]}
        return Response({"walks": [_row(w) for w in qs[:200]], "days": totals, "prefs": _prefs(u)})
    d = request.data
    kind = d.get("kind") if d.get("kind") in KINDS else "walk"
    try:
        started = datetime.fromisoformat(str(d.get("started_at")).replace("Z", "+00:00"))
    except ValueError:
        return Response({"detail": "Bad start time."}, status=400)
    if started.tzinfo is None:
        return Response({"detail": "Start time needs a time zone."}, status=400)
    day = _day(d.get("day"))
    secs, steps = _int(d.get("secs"), 0, 86400), _int(d.get("steps"), 0, 150000)
    dist, kcal = _int(d.get("dist_m"), 0, 400000), _int(d.get("kcal"), 0, 20000)
    path = _clean_path(d.get("path", []))
    if None in (day, secs, steps, dist, kcal, path):
        return Response({"detail": "Some numbers look wrong."}, status=400)
    w, made = Walk.objects.update_or_create(user=u, started_at=started, defaults={
        "kind": kind, "day": day, "secs": secs, "steps": steps, "steps_est": bool(d.get("steps_est")),
        "dist_m": dist, "kcal": kcal, "path": path})
    return Response(_row(w), status=201 if made else 200)


def _day(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def walk(request, wid):
    w = Walk.objects.filter(user=request.user, id=wid).first()
    if not w:
        return Response({"detail": "Not found."}, status=404)
    if request.method == "DELETE":
        w.delete()
        return Response({"ok": True})
    return Response(_row(w, True))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def prefs(request):
    if request.method == "POST":
        p, _ = Prefs.objects.get_or_create(user=request.user)
        g, h, k = (_int(request.data.get("goal"), 500, 100000), _int(request.data.get("height_cm"), 90, 230),
                   _int(request.data.get("weight_kg"), 20, 250))
        if None in (g, h, k):
            return Response({"detail": "Goal 500-100000, height 90-230 cm, weight 20-250 kg."}, status=400)
        p.goal, p.height_cm, p.weight_kg = g, h, k
        p.save()
    return Response(_prefs(request.user))
