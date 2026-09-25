"""System log for the super admin only: timeline with filters, day-by-day summary, most active
members, new members, and a CSV download."""
import csv
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import AuditEvent

User = get_user_model()
PAGE = 100


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


def _name(u):
    if not u:
        return "Visitor"
    return (getattr(u, "full_name", "") or "").strip() or getattr(u, "email", "") or ("User %d" % u.pk)


def _range(g):
    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    try:
        d1 = datetime.strptime(g.get("from") or "", "%Y-%m-%d").date()
    except ValueError:
        d1 = today - timedelta(days=6)
    try:
        d2 = datetime.strptime(g.get("to") or "", "%Y-%m-%d").date()
    except ValueError:
        d2 = today
    if d2 < d1:
        d1, d2 = d2, d1
    return d1, d2, timezone.make_aware(datetime.combine(d1, time.min), tz), timezone.make_aware(datetime.combine(d2, time.max), tz)


def _filtered(g):
    d1, d2, a, b = _range(g)
    qs = AuditEvent.objects.select_related("user").filter(created_at__gte=a, created_at__lte=b)
    if g.get("user"):
        qs = qs.filter(user_id=g.get("user")) if str(g.get("user")).isdigit() else qs.none()
    if g.get("category"):
        qs = qs.filter(category=g.get("category"))
    if g.get("action"):
        qs = qs.filter(action=g.get("action"))
    return qs, d1, d2


def _row(e):
    return {"id": e.id, "when": timezone.localtime(e.created_at).strftime("%d %b %Y, %H:%M:%S"), "user_id": e.user_id,
            "user": _name(e.user), "email": getattr(e.user, "email", "") if e.user else "", "action": e.action,
            "category": e.category, "path": e.path, "object_id": e.object_id, "ip": e.ip or "", "agent": e.agent, "extra": e.extra}


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def events(request):
    qs, d1, d2 = _filtered(request.GET)
    try:
        before = int(request.GET.get("before") or 0)
    except ValueError:
        before = 0
    if before:
        qs = qs.filter(id__lt=before)
    rows = list(qs[:PAGE + 1])
    return Response({"events": [_row(e) for e in rows[:PAGE]], "more": len(rows) > PAGE, "from": str(d1), "to": str(d2)})


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def summary(request):
    qs, d1, d2 = _filtered(request.GET)
    days = {}
    for r in qs.annotate(d=TruncDate("created_at")).values("d").annotate(
            n=Count("id"), users=Count("user", distinct=True),
            joins=Count("id", filter=Q(action__startswith="Joined")),
            logins=Count("id", filter=Q(action="Signed in")),
            failed=Count("id", filter=Q(action="Failed sign-in"))).order_by("-d"):
        days[str(r["d"])] = {"day": str(r["d"]), "actions": r["n"], "active": r["users"], "joins": r["joins"],
                             "logins": r["logins"], "failed": r["failed"]}
    top = [{"user_id": r["user"], "user": _name(User.objects.filter(pk=r["user"]).first()), "actions": r["n"]}
           for r in qs.exclude(user=None).values("user").annotate(n=Count("id")).order_by("-n")[:50]]
    kinds = [{"action": r["action"], "category": r["category"], "n": r["n"]}
             for r in qs.values("action", "category").annotate(n=Count("id")).order_by("-n")[:60]]
    d1a, d2a = _range(request.GET)[2:]
    joined = [{"user_id": u.pk, "user": _name(u), "email": u.email, "when": timezone.localtime(u.date_joined).strftime("%d %b %Y, %H:%M")
               if getattr(u, "date_joined", None) else ""}
              for u in User.objects.filter(date_joined__gte=d1a, date_joined__lte=d2a).order_by("-date_joined")[:200]] \
        if hasattr(User, "date_joined") else []
    return Response({"from": str(d1), "to": str(d2), "total": qs.count(), "days": list(days.values()), "top": top,
                     "kinds": kinds, "joined": joined,
                     "categories": sorted(set(AuditEvent.objects.values_list("category", flat=True).distinct()))})


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def users(request):
    q = str(request.GET.get("q") or "").strip()[:60]
    qs = User.objects.all()
    if q:
        f = Q(email__icontains=q)
        if hasattr(User, "full_name"):
            f |= Q(full_name__icontains=q)
        qs = qs.filter(f)
    return Response({"users": [{"id": u.pk, "name": _name(u), "email": u.email} for u in qs.order_by("-id")[:20]]})


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def export(request):
    qs, d1, d2 = _filtered(request.GET)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="system-log-%s-to-%s.csv"' % (d1, d2)
    resp.write("\ufeff")
    w = csv.writer(resp)
    w.writerow(["When", "User ID", "User", "Email", "Action", "Category", "Page", "Item", "IP", "Device", "Note"])
    for e in qs[:50000]:
        r = _row(e)
        w.writerow([r["when"], r["user_id"] or "", r["user"], r["email"], r["action"], r["category"], r["path"], r["object_id"], r["ip"], r["agent"], r["extra"]])
    return resp
