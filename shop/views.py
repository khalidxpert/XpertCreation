"""Pay per order: profile boost, post boost, featured job, Company Pro, blue tick fee.
Mode: off (nothing for sale), test (staff only, 'simulate payment'), live (members, real gateway - added later)."""
from datetime import timedelta

from django.apps import apps
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import Order, ShopSetting

CATALOG = {
    "profile_boost": {"name": "Profile boost", "what": "Show first in People search, with a Boosted mark.", "target": "self",
                      "plans": {"7d": ("7 days", 499, 7), "30d": ("30 days", 1499, 30)}},
    "post_boost": {"name": "Post boost", "what": "Show your post at the top of For you, marked Boosted.", "target": "post",
                   "plans": {"3d": ("3 days", 299, 3), "7d": ("7 days", 599, 7)}},
    "featured_job": {"name": "Featured job", "what": "Pin your job at the top of Jobs with a Featured badge.", "target": "job",
                     "plans": {"15d": ("15 days", 999, 15), "30d": ("30 days", 1799, 30)}},
    "company_pro": {"name": "Company Pro", "what": "PRO badge, listed first among companies, featured jobs included.", "target": "company",
                    "plans": {"month": ("1 month", 2499, 30), "year": ("1 year", 24999, 365)}},
    "blue_tick": {"name": "Blue tick", "what": "Identity check for the blue tick. Fully refunded if the check is rejected.", "target": "self",
                  "plans": {"once": ("one time", 999, 0)}},
}


def setting():
    s = ShopSetting.objects.first()
    return s or ShopSetting.objects.create()


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def price(product, plan, s=None):
    s = s or setting()
    return int((s.prices or {}).get("%s:%s" % (product, plan), CATALOG[product]["plans"][plan][1]))


def _catalog(s):
    return [{"key": k, "name": c["name"], "what": c["what"], "target": c["target"],
             "plans": [{"key": p, "label": v[0], "price": price(k, p, s), "days": v[2]} for p, v in c["plans"].items()]} for k, c in CATALOG.items()]


# ---- what is active right now (used by people search, feed, jobs, companies)
def _active(product):
    now = timezone.now()
    return Order.objects.filter(product=product, status="paid", starts_at__lte=now, ends_at__gt=now)


def boosted_user_ids():
    return set(_active("profile_boost").values_list("user_id", flat=True))


def boosted_post_ids():
    return set(_active("post_boost").values_list("target_id", flat=True))


def featured_job_ids():
    return set(_active("featured_job").values_list("target_id", flat=True))


def pro_company_ids():
    return set(_active("company_pro").values_list("target_id", flat=True))


def boost_case(field="user_id"):
    ids = list(boosted_user_ids())
    return Case(When(**{field + "__in": ids}, then=Value(1)), default=Value(0), output_field=IntegerField()) if ids else Value(0, output_field=IntegerField())


def blue_tick_paid(user):
    return Order.objects.filter(user=user, product="blue_tick", status="paid").exists()


# ---- targets the member may buy for
def _target(u, kind, tid):
    if kind == "self":
        return u.pk, (getattr(u, "full_name", "") or u.username)
    if not tid:
        return None, "Choose what to promote."
    if kind == "post":
        P = apps.get_model("feed", "Post"); p = P.objects.filter(pk=tid, author=u).first()
        return (p.pk, (str(getattr(p, "text", "") or getattr(p, "body", "") or "Post")[:80])) if p else (None, "That post is not yours.")
    if kind == "job":
        J = apps.get_model("jobs", "Job"); j = J.objects.filter(pk=tid, poster=u, closed=False).first()
        return (j.pk, j.title) if j else (None, "That job is not yours or is closed.")
    if kind == "company":
        C = apps.get_model("companies", "Company"); c = C.objects.filter(pk=tid, owner=u).first()
        if not c:
            return None, "That company is not yours."
        if getattr(c, "status", "") != getattr(C, "APPROVED", "approved"):
            return None, "Company Pro is for verified companies. Finish your company's check first."
        return c.pk, c.name
    return None, "Unknown item."


def _activate(o):
    now = timezone.now(); days = CATALOG[o.product]["plans"][o.plan][2]
    last = _active(o.product).filter(target_id=o.target_id).exclude(pk=o.pk).order_by("-ends_at").first()
    start = last.ends_at if (last and o.product != "blue_tick") else now
    o.status, o.paid_at, o.starts_at = "paid", now, start
    o.ends_at = start + timedelta(days=days) if days else now + timedelta(days=36500)
    o.save()


def _out(o):
    c = CATALOG.get(o.product, {})
    return {"id": o.id, "product": o.product, "name": c.get("name", o.product), "plan": c.get("plans", {}).get(o.plan, (o.plan,))[0], "for": o.target_label,
            "amount": o.amount, "status": o.status, "created": o.created_at.isoformat(), "starts": o.starts_at.isoformat() if o.starts_at else "",
            "ends": o.ends_at.isoformat() if (o.ends_at and o.product != "blue_tick") else "", "provider": o.provider, "ref": o.provider_ref}


@api_view(["GET"])
@permission_classes([AllowAny])
def shop(request):
    s = setting(); u = request.user
    out = {"mode": s.mode, "catalog": _catalog(s), "staff": _staff(u), "can_buy": s.mode == "live" or (s.mode == "test" and _staff(u))}
    if u.is_authenticated:
        out["orders"] = [_out(o) for o in Order.objects.filter(user=u).order_by("-id")[:50]]
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order(request):
    s = setting(); u = request.user; d = request.data
    if not (s.mode == "live" or (s.mode == "test" and _staff(u))):
        return Response({"detail": "Paid items are not available yet."}, status=403)
    p, plan = d.get("product"), d.get("plan")
    if p not in CATALOG or plan not in CATALOG[p]["plans"]:
        return Response({"detail": "Choose an item and a plan."}, status=400)
    if p == "blue_tick" and Order.objects.filter(user=u, product="blue_tick", status="paid").exists():
        return Response({"detail": "You have already paid for the blue tick check."}, status=400)
    tid, label = _target(u, CATALOG[p]["target"], d.get("target"))
    if tid is None:
        return Response({"detail": label}, status=400)
    o = Order.objects.create(user=u, product=p, plan=plan, target_id=tid, target_label=label[:160], amount=price(p, plan, s), provider="test" if s.mode == "test" else "")
    return Response({"order": _out(o), "next": "simulate" if s.mode == "test" else "gateway"}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def simulate(request, pk):
    """Test mode only: pretend the payment succeeded, so the whole flow can be tried."""
    s = setting()
    if s.mode != "test" or not _staff(request.user):
        return Response({"detail": "Only staff, in test mode."}, status=403)
    o = Order.objects.filter(pk=pk, user=request.user, status="pending").first()
    if not o:
        return Response({"detail": "Order not found."}, status=404)
    o.provider_ref = "TEST-%d" % o.id; _activate(o)
    return Response({"order": _out(o)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel(request, pk):
    o = Order.objects.filter(pk=pk, user=request.user, status="pending").first()
    if not o:
        return Response({"detail": "Order not found."}, status=404)
    o.status = "cancelled"; o.save(update_fields=["status"]); return Response({"order": _out(o)})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def admin(request):
    if not _staff(request.user):
        return Response({"detail": "Staff only."}, status=403)
    s = setting()
    if request.method == "POST":
        if request.data.get("mode") in ("off", "test", "live"):
            if request.data["mode"] == "live" and not request.data.get("gateway_ready"):
                return Response({"detail": "Live needs a connected payment gateway first."}, status=400)
            s.mode = request.data["mode"]
        if isinstance(request.data.get("prices"), dict):
            pr = {}
            for k, v in request.data["prices"].items():
                prod, _, plan = k.partition(":")
                if prod in CATALOG and plan in CATALOG[prod]["plans"] and str(v).isdigit() and 0 < int(v) <= 1000000:
                    pr[k] = int(v)
            s.prices = pr
        s.save()
    rows = Order.objects.select_related("user").order_by("-id")[:100]
    paid = Order.objects.filter(status="paid").exclude(provider="test")
    return Response({"mode": s.mode, "catalog": _catalog(s), "orders": [dict(_out(o), user=(getattr(o.user, "full_name", "") or o.user.username)) for o in rows],
                     "totals": {"orders": paid.count(), "rupees": sum(paid.values_list("amount", flat=True))}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refund(request, pk):
    if not _staff(request.user):
        return Response({"detail": "Staff only."}, status=403)
    o = Order.objects.filter(pk=pk, status="paid").first()
    if not o:
        return Response({"detail": "Paid order not found."}, status=404)
    o.status, o.ends_at, o.note = "refunded", timezone.now(), str(request.data.get("note") or "")[:300]
    o.save(update_fields=["status", "ends_at", "note"])
    return Response({"order": _out(o), "note": "Marked refunded and switched off. Send the money back through the payment provider."})
