from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import Review

MODULES = dict(Review.MODULES)


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


class ReviewThrottle(SimpleRateThrottle):
    scope = "reviews"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def summary_for(module):
    qs = Review.objects.filter(module=module)
    agg = qs.aggregate(avg=Avg("stars"), n=Count("id"))
    spread = {i: 0 for i in range(1, 6)}
    for row in qs.values("stars").annotate(n=Count("id")):
        spread[row["stars"]] = row["n"]
    return {
        "module": module,
        "name": MODULES.get(module, module),
        "average": round(agg["avg"], 1) if agg["avg"] else None,
        "count": agg["n"],
        "spread": spread,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def module_reviews(request, module):
    """Stars for everyone, comments only once they have been looked at."""
    if module not in MODULES:
        return _err("Unknown module.", status.HTTP_404_NOT_FOUND)

    out = summary_for(module)

    rows = (Review.objects.filter(module=module, state=Review.PUBLISHED)
            .exclude(comment="")
            .select_related("user")
            .order_by("-created_at")[:20])

    out["reviews"] = [{
        "stars": r.stars,
        "comment": r.comment,
        "name": ("Private" if r.user.hide_from_leaderboard
                 else ((r.user.full_name or "").strip() or r.user.email.split("@")[0])),
        "avatar": r.user.avatar,
        "when": r.created_at.strftime("%d %b %Y"),
    } for r in rows]

    if request.user.is_authenticated:
        mine = Review.objects.filter(user=request.user, module=module).first()
        out["mine"] = ({"stars": mine.stars, "comment": mine.comment,
                        "state": mine.state} if mine else None)

    return Response(out)


@api_view(["GET"])
@permission_classes([AllowAny])
def all_summaries(request):
    """Every module's rating in one call, for the landing page."""
    return Response({"modules": [summary_for(m) for m, _ in Review.MODULES]})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@throttle_classes([ReviewThrottle])
def my_review(request, module):
    """body: { stars: 1-5, comment: "..." }"""
    if module not in MODULES:
        return _err("Unknown module.", status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        Review.objects.filter(user=request.user, module=module).delete()
        return Response({"detail": "Removed."})

    try:
        stars = int(request.data.get("stars"))
    except (TypeError, ValueError):
        return _err("Pick a rating from one to five.")
    if not (1 <= stars <= 5):
        return _err("Pick a rating from one to five.")

    comment = str(request.data.get("comment") or "").strip()[:600]

    r = Review.objects.filter(user=request.user, module=module).first()
    if r:
        # Changing the words sends it back for another look; changing only the
        # stars does not, since there is nothing new to read.
        if comment != r.comment:
            r.state = Review.PENDING if comment else Review.PUBLISHED
            r.reviewed_at = None
        r.stars = stars
        r.comment = comment
        r.save()
    else:
        r = Review.objects.create(user=request.user, module=module,
                                  stars=stars, comment=comment)

    return Response({
        "stars": r.stars, "comment": r.comment, "state": r.state,
        "note": ("Your rating is live. The comment will appear once we have read it."
                 if r.state == Review.PENDING else "Thank you."),
        "summary": summary_for(module),
    }, status=status.HTTP_201_CREATED)
