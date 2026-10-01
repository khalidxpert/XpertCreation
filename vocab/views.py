"""Vocabulary progress for signed-in members (guests keep theirs on the device)."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Progress, Streak

GAPS = [0, 1, 2, 4, 7, 15]          # days until a word comes back, by box
LEARNED = 3                          # box 3 or higher counts as learned


def _state(u):
    s = Streak.objects.filter(user=u).first()
    today = timezone.localdate()
    days = s.days if s and s.last_day and (today - s.last_day).days <= 1 else 0
    rows = Progress.objects.filter(user=u).values_list("word", "box", "due")
    return {"progress": {w: [b, d.isoformat()] for w, b, d in rows}, "streak": days, "best": s.best if s else 0,
            "learned": sum(1 for _, b, _ in rows if b >= LEARNED), "today_done": bool(s and s.last_day == today)}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(_state(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answer(request):
    """{word, ok} - move the word up a box when known, back to the start when missed; keep the daily streak."""
    try:
        wid = int(request.data.get("word"))
    except (TypeError, ValueError):
        return Response({"detail": "Which word?"}, status=400)
    if not 1 <= wid <= 100000:
        return Response({"detail": "Which word?"}, status=400)
    ok = bool(request.data.get("ok"))
    today = timezone.localdate()
    p, _ = Progress.objects.get_or_create(user=request.user, word=wid, defaults={"due": today})
    p.box = min(5, p.box + 1) if ok else 0
    p.due = today + timedelta(days=GAPS[p.box])
    p.seen += 1; p.right += 1 if ok else 0
    p.save()
    s, _ = Streak.objects.get_or_create(user=request.user)
    if s.last_day != today:
        s.days = s.days + 1 if s.last_day == today - timedelta(days=1) else 1
        s.last_day = today; s.best = max(s.best, s.days); s.save()
    return Response({"word": wid, "box": p.box, "due": p.due.isoformat(), "streak": s.days, "best": s.best})
