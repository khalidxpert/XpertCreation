"""Company register API (/api/companybook/), team only."""
import csv
import io
from datetime import date, timedelta

from django.apps import apps
from django.db import IntegrityError
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Entry

REAL = "safepay-production"
GROUP = {"profile_boost": "Ads & boosts", "post_boost": "Ads & boosts", "featured_job": "Ads & boosts", "gig_boost": "Ads & boosts",
         "property_boost": "Ads & boosts", "product_boost": "Ads & boosts", "company_pro": "Company Pro", "blue_tick": "Blue tick checks",
         "merchant_gold": "Merchant plans", "merchant_platinum": "Merchant plans"}
CATS_IN = ["Ads & boosts", "Company Pro", "Blue tick checks", "Merchant plans", "Freelance commission", "Store commission", "Courses", "Other income"]
CATS_OUT = ["Refunds", "Rewards campaign payouts", "Referral commissions", "Hosting & domains", "Salaries", "Marketing", "Software & tools",
            "Payment gateway fees", "Taxes", "Office", "Other expense"]


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _model(label):
    try:
        return apps.get_model(*label.split("."))
    except LookupError:
        return None


def _put(ref, **kw):
    try:
        Entry.objects.get_or_create(ref=ref, defaults=kw)
    except IntegrityError:
        pass


def _d(t):
    return timezone.localtime(t).date() if t else timezone.localdate()


def sync():
    """Copy new money events from every platform into the register. Safe to run again: each event is stored once."""
    n0 = Entry.objects.count()
    SO = _model("shop.Order")
    if SO:
        try:
            from shop.views import CATALOG
        except Exception:
            CATALOG = {}
        for o in SO.objects.filter(status__in=("paid", "refunded")).exclude(provider="").only("id", "product", "plan", "amount", "paid_at", "ends_at", "status", "provider", "user_id"):
            t = o.provider != REAL
            name = CATALOG.get(o.product, {}).get("name", o.product)
            _put("shop:%d" % o.id, day=_d(o.paid_at), kind="income", source="shop", category=GROUP.get(o.product, "Other income"), amount=o.amount,
                 note="%s (%s), order %d" % (name, o.plan, o.id), test=t)
            if o.status == "refunded":
                _put("shop-refund:%d" % o.id, day=_d(o.ends_at), kind="expense", source="shop", category="Refunds", amount=o.amount, note="Refund of order %d" % o.id, test=t)
    MO = _model("market.Order")
    if MO:
        for o in MO.objects.filter(status="completed", fee__gt=0).only("id", "fee", "done_at", "provider", "title"):
            _put("market:%d" % o.id, day=_d(o.done_at), kind="income", source="market", category="Freelance commission", amount=o.fee,
                 note="XM-%06d %s" % (o.id, o.title[:80]), test=o.provider != REAL)
    TO = _model("store.Order")
    if TO:
        for o in TO.objects.filter(status="completed", payment="online", fee__gt=0).only("id", "fee", "done_at", "provider"):
            _put("store:%d" % o.id, day=_d(o.done_at), kind="income", source="store", category="Store commission", amount=o.fee,
                 note="XS-%06d" % o.id, test=o.provider != REAL)
    W = _model("rewards.Withdrawal")
    if W:
        for w in W.objects.filter(status="paid").only("id", "amount", "handled_at", "method"):
            _put("rw:%d" % w.id, day=_d(w.handled_at), kind="expense", source="rewards", category="Rewards campaign payouts", amount=w.amount,
                 note="Rewards withdrawal #%d (%s)" % (w.id, w.method))
    C = _model("rewards.Commission")
    if C:
        for c in C.objects.filter(status="released").only("id", "amount", "release_at", "level"):
            _put("rc:%d" % c.id, day=_d(c.release_at), kind="expense", source="rewards", category="Referral commissions", amount=c.amount,
                 note="Referral share level %d" % c.level)
    return Entry.objects.count() - n0


def _row(e):
    return {"id": e.id, "day": e.day.isoformat(), "kind": e.kind, "source": e.source, "category": e.category, "amount": e.amount, "note": e.note,
            "test": e.test, "manual": e.source == "manual", "by": (e.created_by.username if e.created_by_id else "")}


def _range(g):
    today = timezone.localdate()
    try:
        f = date.fromisoformat(g.get("from")) if g.get("from") else today.replace(day=1) - timedelta(days=365)
        t = date.fromisoformat(g.get("to")) if g.get("to") else today
    except ValueError:
        f, t = today - timedelta(days=365), today
    return f, t


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def book(request):
    if not _staff(request.user):
        return Response({"detail": "Team only."}, status=403)
    added = sync()
    g = request.GET
    f, t = _range(g)
    qs = Entry.objects.filter(day__gte=f, day__lte=t).select_related("created_by")
    if not g.get("test"):
        qs = qs.filter(test=False)
    inc = qs.filter(kind="income").aggregate(s=Sum("amount"))["s"] or 0
    exp = qs.filter(kind="expense").aggregate(s=Sum("amount"))["s"] or 0
    cats = {}
    for r in qs.values("kind", "category").annotate(s=Sum("amount")).order_by("-s"):
        cats.setdefault(r["kind"], []).append({"category": r["category"], "amount": r["s"]})
    months = {}
    for e in qs.values("day", "kind", "amount"):
        k = e["day"].strftime("%Y-%m"); m = months.setdefault(k, {"month": k, "income": 0, "expense": 0}); m[e["kind"]] += e["amount"]
    owed = 0
    E = _model("market.Entry")
    if E:
        owed = E.objects.aggregate(s=Sum("amount"))["s"] or 0
    rows = qs if g.get("cat") is None else qs.filter(category=g.get("cat"))
    return Response({"from": f.isoformat(), "to": t.isoformat(), "income": inc, "expense": exp, "net": inc - exp, "new_lines": added,
                     "by_category": cats, "months": sorted(months.values(), key=lambda x: x["month"]),
                     "owed_to_sellers": owed, "cats_in": CATS_IN, "cats_out": CATS_OUT,
                     "entries": [_row(e) for e in rows[:1000]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add(request):
    if not _staff(request.user):
        return Response({"detail": "Team only."}, status=403)
    d = request.data
    kind = d.get("kind") if d.get("kind") in ("income", "expense") else None
    cat = str(d.get("category") or "").strip()[:60]
    try:
        amount = int(str(d.get("amount")).replace(",", ""))
        day = date.fromisoformat(str(d.get("day")))
    except (TypeError, ValueError):
        amount, day = 0, None
    if not kind or not cat or amount <= 0 or not day:
        return Response({"detail": "Choose income or expense, a category, the date and the amount."}, status=400)
    e = Entry.objects.create(day=day, kind=kind, source="manual", category=cat, amount=amount, note=str(d.get("note") or "")[:300], created_by=request.user)
    return Response(_row(e), status=201)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete(request, pk):
    if not _staff(request.user):
        return Response({"detail": "Team only."}, status=403)
    e = Entry.objects.filter(pk=pk, source="manual").first()
    if not e:
        return Response({"detail": "Only lines you added by hand can be deleted."}, status=404)
    e.delete()
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export(request):
    if not _staff(request.user):
        return Response({"detail": "Team only."}, status=403)
    sync()
    f, t = _range(request.GET)
    qs = Entry.objects.filter(day__gte=f, day__lte=t).order_by("day", "id")
    if not request.GET.get("test"):
        qs = qs.filter(test=False)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["Date", "Type", "Source", "Category", "Amount (PKR)", "Note", "Test"])
    for e in qs:
        w.writerow([e.day.isoformat(), e.kind, e.source, e.category, e.amount if e.kind == "income" else -e.amount, e.note, "yes" if e.test else ""])
    r = HttpResponse(buf.getvalue(), content_type="text/csv")
    r["Content-Disposition"] = 'attachment; filename="xpertcreation-register-%s-to-%s.csv"' % (f, t)
    return r
