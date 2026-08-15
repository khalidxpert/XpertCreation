import random
from datetime import timedelta

from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import Drill, Score, Session, Stats

# A verified human record is around 216 wpm. Anything past this is either a
# script or a paste, and is refused rather than quietly stored.
WPM_CEILING = 200


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")


class RunThrottle(SimpleRateThrottle):
    scope = "typing"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def grade(expected, typed, seconds):
    """
    Works out wpm and accuracy from the two strings.

    Compared character by character against what was actually served. Counting
    the client's own "correct" tally would make every number a suggestion.
    """
    typed = typed or ""
    correct = 0
    for i, ch in enumerate(typed):
        if i < len(expected) and ch == expected[i]:
            correct += 1

    typed_n = len(typed)
    accuracy = round(correct / typed_n * 100) if typed_n else 0

    # The standard: a "word" is five characters, and only correct ones count.
    minutes = seconds / 60.0
    wpm = int(round((correct / 5.0) / minutes)) if minutes > 0 else 0
    return wpm, accuracy, correct, typed_n


@api_view(["GET"])
@permission_classes([AllowAny])
def drills(request):
    """The catalogue. Content is deliberately left out - it arrives only when a
    run is started, so it cannot be pre-loaded and pasted."""
    qs = Drill.objects.filter(is_active=True)
    kind = request.GET.get("kind")
    if kind:
        qs = qs.filter(kind=kind)

    done = []
    if request.user.is_authenticated:
        st = Stats.objects.filter(user=request.user).first()
        done = (st.lessons_done if st else []) or []

    return Response({"drills": [{
        "id": d.id, "kind": d.kind, "level": d.level, "title": d.title,
        "hint": d.hint, "lang": d.lang, "length": len(d.content),
        "done": d.id in done,
    } for d in qs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([RunThrottle])
def start(request):
    """body: { drill: <id> }  or  { kind: "test", level: 1 }"""
    drill = None
    if request.data.get("drill"):
        drill = Drill.objects.filter(id=request.data["drill"], is_active=True).first()
    else:
        pool = list(Drill.objects.filter(
            kind=request.data.get("kind", "test"), is_active=True))
        drill = random.choice(pool) if pool else None

    if not drill:
        return Response({"detail": "No exercise available."},
                        status=status.HTTP_404_NOT_FOUND)

    # Only one run may be open at a time - otherwise somebody could keep
    # several going and submit whichever produced the best number. The old one
    # is closed rather than deleted, so it still shows in the history.
    Session.objects.filter(user=request.user, finished_at__isnull=True)\
        .update(finished_at=timezone.now())

    s = Session.open(request.user, drill, client_ip(request))
    return Response({
        "token": s.token,
        "drill": {"id": drill.id, "kind": drill.kind, "title": drill.title,
                  "hint": drill.hint, "lang": drill.lang, "content": drill.content},
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([RunThrottle])
def finish(request):
    """body: { token, typed }"""
    s = Session.objects.filter(token=request.data.get("token") or "",
                               user=request.user,
                               finished_at__isnull=True).select_related("drill").first()
    if not s:
        return Response({"detail": "No run in progress."},
                        status=status.HTTP_404_NOT_FOUND)

    seconds = s.elapsed
    s.finished_at = timezone.now()
    s.save(update_fields=["finished_at"])

    if seconds > Session.MAX_SECONDS:
        return Response({"detail": "That run timed out. Start again."},
                        status=status.HTTP_410_GONE)
    if seconds < Session.MIN_SECONDS:
        return Response({"detail": "That was too fast to be a real attempt."},
                        status=status.HTTP_400_BAD_REQUEST)

    typed = str(request.data.get("typed") or "")[:5000]
    wpm, accuracy, correct, typed_n = grade(s.drill.content, typed, seconds)

    if wpm > WPM_CEILING:
        return Response({"detail": "That result could not be verified. "
                                   "If this is genuine, contact support.",
                         "wpm": wpm}, status=status.HTTP_400_BAD_REQUEST)

    score = Score.objects.create(
        user=request.user, drill=s.drill, mode=s.drill.kind,
        wpm=wpm, accuracy=accuracy, correct_chars=correct,
        typed_chars=typed_n, seconds=int(seconds))

    st, _ = Stats.objects.get_or_create(user=request.user)
    st.record(score)

    # A lesson counts as done at 90% accuracy: finishing it badly is not
    # finishing it.
    if s.drill.kind == Drill.LESSON and accuracy >= 90 and s.drill.id not in (st.lessons_done or []):
        st.lessons_done = (st.lessons_done or []) + [s.drill.id]
        st.save(update_fields=["lessons_done"])

    best = Score.objects.filter(user=request.user, mode=s.drill.kind).aggregate(m=Max("wpm"))["m"] or 0

    return Response({
        "wpm": wpm, "accuracy": accuracy, "seconds": int(seconds),
        "correct_chars": correct, "typed_chars": typed_n,
        "expected_chars": len(s.drill.content),
        "personal_best": best, "is_best": wpm >= best,
        "streak": st.current_streak, "badge": st.badge,
        "lesson_passed": s.drill.kind == Drill.LESSON and accuracy >= 90,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def leaderboard(request):
    """?period=week|all  &  ?mode=test|game"""
    mode = request.GET.get("mode", "test")
    period = request.GET.get("period", "week")

    qs = Score.objects.filter(mode=mode)
    if period == "week":
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=7))

    # One row per person: their best. Otherwise the board is one fast typist
    # twenty times over.
    rows = (qs.values("user_id", "user__full_name", "user__email",
                      "user__hide_from_leaderboard")
              .annotate(best=Max("wpm"))
              .order_by("-best")[:25])

    out, me = [], None
    for i, r in enumerate(rows, 1):
        name = ("Private typist" if r["user__hide_from_leaderboard"]
                else ((r["user__full_name"] or "").strip() or r["user__email"].split("@")[0]))
        item = {"rank": i, "name": name, "wpm": r["best"]}
        out.append(item)
        if request.user.is_authenticated and r["user_id"] == request.user.id:
            me = item

    # Outside the top 25, people still want to know where they stand.
    if request.user.is_authenticated and me is None:
        mine = qs.filter(user=request.user).aggregate(m=Max("wpm"))["m"]
        if mine:
            ahead = (qs.values("user_id").annotate(b=Max("wpm"))
                       .filter(b__gt=mine).count())
            name = (request.user.full_name or "").strip() or request.user.email.split("@")[0]
            me = {"rank": ahead + 1, "name": name, "wpm": mine}

    return Response({"period": period, "mode": mode, "top": out, "me": me})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_stats(request):
    st, _ = Stats.objects.get_or_create(user=request.user)
    recent = Score.objects.filter(user=request.user).order_by("-created_at")[:10]
    return Response({
        "best_wpm": st.best_wpm, "best_accuracy": st.best_accuracy,
        "total_runs": st.total_runs, "total_minutes": st.total_seconds // 60,
        "streak": st.current_streak, "longest_streak": st.longest_streak,
        "badge": st.badge, "lessons_done": st.lessons_done or [],
        "recent": [{"wpm": s.wpm, "accuracy": s.accuracy, "mode": s.mode,
                    "at": s.created_at.strftime("%d %b %H:%M")} for s in recent],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resume(request):
    """
    Is there a run still open, and how far in was it?

    Answers with the drill and how long it has been sitting there, so the page
    can offer to carry on rather than silently throwing the attempt away.
    """
    s = (Session.objects.filter(user=request.user, finished_at__isnull=True)
         .select_related("drill").first())
    if not s:
        return Response({"open": False})

    if s.elapsed > Session.MAX_SECONDS:
        s.finished_at = timezone.now()
        s.save(update_fields=["finished_at"])
        return Response({"open": False, "expired": True})

    return Response({
        "open": True,
        "token": s.token,
        "elapsed": int(s.elapsed),
        "drill": {"id": s.drill.id, "kind": s.drill.kind, "title": s.drill.title,
                  "hint": s.drill.hint, "lang": s.drill.lang,
                  "content": s.drill.content},
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def abandon(request):
    """Give up on the open run without recording a score."""
    n = (Session.objects.filter(user=request.user, finished_at__isnull=True)
         .update(finished_at=timezone.now()))
    return Response({"closed": n})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def progress(request):
    """
    Which drill to offer next: the first one in the current level that has not
    been passed yet. Somebody coming back after a week should not have to
    remember where they were.
    """
    st, _ = Stats.objects.get_or_create(user=request.user)
    done = set(st.lessons_done or [])

    nxt = (Drill.objects.filter(kind=Drill.LESSON, is_active=True)
           .exclude(id__in=done).order_by("level", "order", "id").first())

    total = Drill.objects.filter(kind=Drill.LESSON, is_active=True).count()
    return Response({
        "done": len(done),
        "total": total,
        "percent": round(len(done) / total * 100) if total else 0,
        "next": ({"id": nxt.id, "title": nxt.title, "level": nxt.level}
                 if nxt else None),
        "finished_all": nxt is None and total > 0,
    })
