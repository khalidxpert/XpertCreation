"""Govt jobs, results, admissions and scholarships: added by staff with the official link; expired ones drop off."""
from datetime import date

from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Notice


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _out(n):
    left = (n.last_date - timezone.localdate()).days if n.last_date else None
    return {"id": n.id, "kind": n.kind, "title": n.title, "org": n.org, "city": n.city, "last_date": n.last_date.isoformat() if n.last_date else "",
            "days_left": left, "link": n.link, "details": n.details, "added": n.created_at.date().isoformat()}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def notices(request):
    if request.method == "GET":
        qs = Notice.objects.filter(active=True).filter(Q(last_date__isnull=True) | Q(last_date__gte=timezone.localdate()))
        k = request.GET.get("kind")
        if k in dict(Notice.KINDS):
            qs = qs.filter(kind=k)
        rows = sorted(qs[:300], key=lambda n: (n.last_date is None, n.last_date or date.max, -n.id))
        return Response({"notices": [_out(n) for n in rows[:100]], "staff": _staff(request.user)})
    if not _staff(request.user):
        return Response({"detail": "Only staff can add notices."}, status=403)
    d = request.data; kind = d.get("kind"); link = str(d.get("link") or "").strip(); title = str(d.get("title") or "").strip()
    if kind not in dict(Notice.KINDS) or not title or not link.startswith("http"):
        return Response({"detail": "Choose a type, add a title and the official link (starting with http)."}, status=400)
    ld = None
    if d.get("last_date"):
        try:
            ld = date.fromisoformat(str(d.get("last_date")))
        except ValueError:
            return Response({"detail": "Last date should look like 2026-10-31."}, status=400)
    n = Notice.objects.create(kind=kind, title=title[:160], org=str(d.get("org") or "")[:120], city=str(d.get("city") or "")[:80], last_date=ld,
                              link=link[:400], details=str(d.get("details") or "")[:2000], created_by=request.user)
    return Response(_out(n), status=201)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def one(request, pk):
    if not _staff(request.user):
        return Response({"detail": "Only staff can remove notices."}, status=403)
    Notice.objects.filter(pk=pk).update(active=False)
    return Response({"removed": True})
