"""Daily MCQs for PPSC, FPSC, CSS, NTS and MDCAT practice: 10 a day, scored once, weekly leaderboard, practice by topic."""
import json
import os
import random
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Attempt

Q = json.load(open(os.path.join(os.path.dirname(__file__), "questions.json"), encoding="utf-8"))
BY = {q["id"]: q for q in Q}
CATS = {"pak": "Pakistan affairs", "gk": "General knowledge", "isl": "Islamic studies", "eng": "English", "sci": "Everyday science", "cs": "Computers"}


def _today_set(day):
    return random.Random(day.toordinal() * 7919).sample(Q, 10)


def _public(q):
    return {"id": q["id"], "cat": CATS.get(q["cat"], q["cat"]), "q": q["q"], "o": q["o"]}


def _check(qs, answers):
    res, score = [], 0
    for q in qs:
        a = answers.get(str(q["id"]))
        ok = a is not None and str(a).isdigit() and int(a) == q["a"]
        score += ok
        res.append({"id": q["id"], "chosen": int(a) if a is not None and str(a).isdigit() else None, "answer": q["a"], "ok": ok, "why": q["x"]})
    return score, res


def _streak(u):
    days = set(Attempt.objects.filter(user=u).values_list("day", flat=True))
    d, n = timezone.localdate(), 0
    if d not in days:
        d -= timedelta(days=1)
    while d in days:
        n += 1; d -= timedelta(days=1)
    return n


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def today(request):
    day = timezone.localdate(); qs = _today_set(day); u = request.user
    done = Attempt.objects.filter(user=u, day=day).first() if u.is_authenticated else None
    if request.method == "GET":
        out = {"day": day.isoformat(), "questions": [_public(q) for q in qs]}
        if done:
            out["done"] = {"score": done.score, "results": _check(qs, done.answers)[1]}
        return Response(out)
    answers = {str(k): v for k, v in (request.data.get("answers") or {}).items()}
    if done:
        return Response({"score": done.score, "results": _check(qs, done.answers)[1], "saved": False, "note": "You already did today's set; this is your first score."})
    score, res = _check(qs, answers)
    if u.is_authenticated:
        Attempt.objects.create(user=u, day=day, score=score, answers=answers)
    return Response({"score": score, "results": res, "saved": u.is_authenticated, "streak": _streak(u) if u.is_authenticated else 0})


@api_view(["GET"])
@permission_classes([AllowAny])
def practice(request):
    cat = request.GET.get("cat") or ""
    pool = [q for q in Q if q["cat"] == cat] or Q
    pick = random.sample(pool, min(10, len(pool)))
    return Response({"cats": CATS, "questions": [dict(_public(q), a=q["a"], x=q["x"]) for q in pick]})


@api_view(["GET"])
@permission_classes([AllowAny])
def board(request):
    since = timezone.localdate() - timedelta(days=6)
    rows = list(Attempt.objects.filter(day__gte=since).values("user_id").annotate(points=Sum("score")).order_by("-points")[:20])
    from django.contrib.auth import get_user_model
    users = {x.pk: x for x in get_user_model().objects.filter(pk__in=[r["user_id"] for r in rows])}
    def nm(x):
        return ((getattr(x, "full_name", "") or "").strip() or getattr(x, "username", "") or "Member") if x else "Member"
    top = [{"name": nm(users.get(r["user_id"])), "username": getattr(users.get(r["user_id"]), "username", "") or "", "points": r["points"]} for r in rows]
    me = {}
    if request.user.is_authenticated:
        mine = Attempt.objects.filter(user=request.user, day__gte=since).aggregate(p=Sum("score"))["p"] or 0
        me = {"points": mine, "streak": _streak(request.user)}
    return Response({"top": top, "me": me, "total_questions": len(Q)})
