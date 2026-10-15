"""Freelance marketplace API (/api/market/). See models.py for the flow."""
import re
import urllib.parse
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CATS, CV, Bid, CancelRequest, CustomOffer, CustomRequest, Entry, Gig, Message, Milestone, Order, OrderFile, Payout, Project, Review

FEE_PCT = 10                     # XpertCreation keeps 10% of every order, from the seller's side
AUTO_DONE_DAYS = 3               # a delivered order completes by itself after this many days
MIN_PAYOUT = 500
MIN_PRICE, MAX_PRICE = 500, 500000
SITE = "https://xpertcreation.com"
CAT_KEYS = dict(CATS)
TIERS = [("basic", "Basic"), ("standard", "Standard"), ("premium", "Premium")]
OFFER_DAYS = 7                   # a custom offer can be accepted for this many days
LATE_CANCEL_HOURS = 48           # the buyer can cancel (full refund) once an order is this late
CANCEL_AUTO_DAYS = 3             # a cancel request with no reply is agreed after this many days
PENDING_HOURS = 24               # an unpaid order is cancelled after this long
MAX_FILE_MB, MAX_FILES = 8, 20
FILE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".zip", ".rar", ".7z", ".doc", ".docx", ".xls", ".xlsx", ".xlsm",
            ".ppt", ".pptx", ".txt", ".csv", ".psd", ".ai", ".svg", ".mp3", ".mp4", ".mov")


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _kyc(u):
    k = getattr(u, "person_kyc", None)
    try:
        if k and k.status == "approved":
            return True
    except Exception:
        pass
    # the same rule as the blue tick on XpertConnect: a verified profile, or staff / admin / moderator
    if u.is_staff or u.is_superuser or getattr(u, "is_moderator", False):
        return True
    try:
        from network.models import ProProfile
        return ProProfile.objects.filter(user=u, verified=True).exists()
    except Exception:
        return False


def _name(u):
    return ((getattr(u, "full_name", "") or u.username or "Member #%d" % u.pk) if u else "Deleted member")[:60]


def _avatar(u):
    try:
        from accounts.views import avatar_url
        return avatar_url(getattr(u, "avatar", "")) or ""
    except Exception:
        return ""


def _who(u):
    return ({"id": u.pk, "name": _name(u), "username": u.username or "", "avatar": _avatar(u)} if u else
            {"id": 0, "name": "Deleted member", "username": "", "avatar": ""})


def _level(done, rating):
    """Seller level from real completed orders and stars (shown on every card)."""
    if done >= 50 and (rating or 0) >= 4.8:
        return "Top rated"
    if done >= 20 and (rating or 0) >= 4.6:
        return "Level 2"
    if done >= 5 and (rating or 0) >= 4.5:
        return "Level 1"
    return "New seller"


def _seller_stats(uid):
    done = Order.objects.filter(seller_id=uid, status="completed").count()
    agg = Review.objects.filter(order__seller_id=uid).aggregate(s=Sum("rating"))
    n = Review.objects.filter(order__seller_id=uid).count()
    r = round((agg["s"] or 0) / n, 1) if n else None
    return {"done": done, "rating": r, "ratings": n, "level": _level(done, r)}


def _txt(v, n):
    return re.sub(r"[ \t]+", " ", str(v or "")).replace("\r\n", "\n").strip()[:n]


def _int(v, lo, hi):
    try:
        v = int(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def _err(msg, code=400):
    return Response({"detail": msg}, status=code)


def _notify(user, text, link):
    try:
        from notifications.views import notify
        notify(user, "market", text, link)
    except Exception:
        pass


def _shop():
    from shop import views as sv
    return sv


def _mode():
    try:
        return _shop().setting().mode
    except Exception:
        return "off"


def _can_buy(u):
    m = _mode()
    return m == "live" or (m == "test" and _staff(u))


def _balance(u):
    return Entry.objects.filter(user=u).aggregate(s=Sum("amount"))["s"] or 0


def featured_ids(product):
    """Targets of paid boosts running right now (Service boost / Property boost from the Promote page)."""
    try:
        from shop.models import Order as ShopOrder
        now = timezone.now()
        return set(ShopOrder.objects.filter(product=product, status="paid", starts_at__lte=now, ends_at__gt=now).values_list("target_id", flat=True))
    except Exception:
        return set()


def _sys(o, text):
    Message.objects.create(order=o, sender=None, text=text)


# ---------------------------------------------------------------- listings
def _gig(g, full=False):
    d = {"id": g.id, "title": g.title, "category": g.category, "cat": CAT_KEYS.get(g.category, ""), "price": g.price, "days": g.days,
         "revisions": g.revisions, "active": g.active and not g.hidden, "orders": g.orders_done,
         "rating": round(g.rating_sum / g.rating_n, 1) if g.rating_n else None, "ratings": g.rating_n, "seller": _who(g.seller),
         "summary": g.description[:160], "images": ["/media/" + p for p in (g.images or [])], "when": g.created_at.isoformat(),
         "packages": g.packages or [], "views": g.views}
    if full:
        d["seller_stats"] = _seller_stats(g.seller_id)
        d["seller_since"] = getattr(g.seller, "date_joined", g.created_at).isoformat()
        d["more"] = [_gig(x) for x in Gig.objects.filter(seller_id=g.seller_id, active=True, hidden=False).exclude(pk=g.pk).select_related("seller")[:4]]
        d["description"] = g.description
        d["reviews"] = [{"rating": r.rating, "text": r.text, "by": _name(r.order.buyer), "when": r.created_at.isoformat()}
                        for r in Review.objects.filter(order__gig=g).select_related("order__buyer").order_by("-id")[:20]]
    return d


@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    u = request.user
    me = None
    if u.is_authenticated:
        me = {"id": u.pk, "name": _name(u), "kyc": _kyc(u), "staff": _staff(u), "balance": _balance(u), "can_buy": _can_buy(u),
              "username": u.username or "",
              "unread": sum(o.unread for o in _with_unread(Order.objects.filter(Q(buyer=u) | Q(seller=u)).exclude(status__in=("pending", "cancelled")).order_by("-id")[:200], u)),
              "requests_in": CustomRequest.objects.filter(seller=u, status="open").count(),
              "offers_in": CustomOffer.objects.filter(buyer=u, status="pending", expires_at__gt=timezone.now()).count()}
    return Response({"cats": CATS, "fee_pct": FEE_PCT, "mode": _mode(), "min_price": MIN_PRICE, "min_payout": MIN_PAYOUT,
                     "auto_days": AUTO_DONE_DAYS, "tiers": TIERS, "offer_days": OFFER_DAYS, "late_hours": LATE_CANCEL_HOURS,
                     "cancel_days": CANCEL_AUTO_DAYS, "max_file_mb": MAX_FILE_MB, "me": me})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def gigs(request):
    u = request.user
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in first.", 401)
        if not _kyc(u):
            return _err("Only members with a verified ID can sell. Get verified first.", 403)
        return _save_gig(request, Gig(seller=u))
    qs = Gig.objects.filter(hidden=False).select_related("seller")
    if request.GET.get("mine") and u.is_authenticated:
        qs = qs.filter(seller=u)
    else:
        qs = qs.filter(active=True, seller__is_active=True)
    if request.GET.get("seller"):
        qs = qs.filter(seller__username__iexact=request.GET["seller"][:30])
    if request.GET.get("cat") in CAT_KEYS:
        qs = qs.filter(category=request.GET["cat"])
    q = _txt(request.GET.get("q"), 60)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    lo, hi, dd = _int(request.GET.get("min"), 0, MAX_PRICE), _int(request.GET.get("max"), 0, MAX_PRICE), _int(request.GET.get("days"), 1, 60)
    if lo:
        qs = qs.filter(price__gte=lo)
    if hi:
        qs = qs.filter(price__lte=hi)
    if dd:
        qs = qs.filter(days__lte=dd)
    sort = {"new": ["-id"], "low": ["price", "-id"], "high": ["-price", "-id"], "rated": ["-rating_sum", "-orders_done", "-id"]}.get(request.GET.get("sort"), ["-orders_done", "-rating_sum", "-id"])
    fid = featured_ids("gig_boost")
    if fid and not request.GET.get("mine"):
        from django.db.models import Case, IntegerField, Value, When
        qs = qs.annotate(fx=Case(When(pk__in=list(fid), then=Value(1)), default=Value(0), output_field=IntegerField()))
        sort = ["-fx"] + sort
    rows = list(qs.order_by(*sort)[:60])
    lv = {}
    out = []
    for g in rows:
        if g.seller_id not in lv:
            lv[g.seller_id] = _seller_stats(g.seller_id)["level"]
        d = _gig(g); d["level"] = lv[g.seller_id]; d["featured"] = g.id in fid; out.append(d)
    counts = dict(Gig.objects.filter(active=True, hidden=False).values_list("category").annotate(n=__import__("django.db.models", fromlist=["Count"]).Count("id")))
    return Response({"gigs": out, "total": qs.count(), "counts": counts})


def _save_gig(request, g):
    d = request.data
    title, desc = _txt(d.get("title"), 100), _txt(d.get("description"), 4000)
    price, days, rev = _int(d.get("price"), MIN_PRICE, MAX_PRICE), _int(d.get("days"), 1, 60), _int(d.get("revisions"), 0, 10)
    if len(title) < 8 or len(desc) < 30:
        return _err("Give a clear title (8+ letters) and describe what the buyer gets (30+ letters).")
    pk = d.get("packages")
    if isinstance(pk, list) and pk:
        clean = []
        for x in pk[:3]:
            if not isinstance(x, dict) or x.get("tier") not in dict(TIERS):
                continue
            p_, d_, r_ = _int(x.get("price"), MIN_PRICE, MAX_PRICE), _int(x.get("days"), 1, 60), _int(x.get("revisions"), 0, 10)
            nm, ds = _txt(x.get("name"), 40) or dict(TIERS)[x["tier"]], _txt(x.get("desc"), 300)
            if p_ is None or d_ is None or r_ is None:
                return _err("%s package: price Rs %d to Rs %d, delivery 1 to 60 days, revisions 0 to 10." % (dict(TIERS)[x["tier"]], MIN_PRICE, MAX_PRICE))
            if len(ds) < 10:
                return _err("%s package: say what is included (10+ letters)." % dict(TIERS)[x["tier"]])
            clean.append({"tier": x["tier"], "name": nm, "desc": ds, "price": p_, "days": d_, "revisions": r_})
        order_ = [k for k, _ in TIERS]
        clean.sort(key=lambda x: order_.index(x["tier"]))
        if len({x["tier"] for x in clean}) != len(clean):
            return _err("Each package can be used once.")
        if any(clean[i]["price"] <= clean[i - 1]["price"] for i in range(1, len(clean))):
            return _err("Each package should cost more than the one before it.")
        if clean:
            price, days, rev = clean[0]["price"], clean[0]["days"], clean[0]["revisions"]
        g.packages = clean
    elif isinstance(pk, list):
        g.packages = []
    if not (isinstance(pk, list) and pk):
        if price is None or days is None or rev is None:
            return _err("Price Rs %d to Rs %d, delivery 1 to 60 days, revisions 0 to 10." % (MIN_PRICE, MAX_PRICE))
    g.title, g.description, g.price, g.days, g.revisions = title, desc, price, days, rev
    g.category = d.get("category") if d.get("category") in CAT_KEYS else "other"
    if "active" in d:
        g.active = bool(d.get("active"))
    g.save()
    return Response(_gig(g, True))


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def gig(request, pk):
    g = Gig.objects.select_related("seller").filter(pk=pk).first()
    if not g or (g.hidden and not _staff(request.user)):
        return _err("Gig not found.", 404)
    if request.method == "POST":
        if not request.user.is_authenticated or g.seller_id != request.user.pk:
            return _err("Only the seller can change this gig.", 403)
        return _save_gig(request, g)
    if not (request.user.is_authenticated and request.user.pk == g.seller_id):
        Gig.objects.filter(pk=g.pk).update(views=F("views") + 1)
    d = _gig(g, True); d["featured"] = g.id in featured_ids("gig_boost")
    d["cv"] = CV.objects.filter(user_id=g.seller_id, public=True).exists()
    return Response(d)


def _project(p, viewer, full=False):
    d = {"id": p.id, "title": p.title, "category": p.category, "cat": CAT_KEYS.get(p.category, ""), "budget": p.budget, "days": p.days,
         "status": p.status, "bids": p.bids_count, "buyer": _who(p.buyer), "when": p.created_at.isoformat(), "summary": p.description[:160],
         "mine": viewer.is_authenticated and p.buyer_id == viewer.pk}
    if full:
        d["description"] = p.description
        bs = p.bids.select_related("seller")
        if not d["mine"] and not _staff(viewer):
            bs = bs.filter(seller_id=viewer.pk if viewer.is_authenticated else 0)
        d["bid_list"] = [{"id": b.id, "amount": b.amount, "days": b.days, "note": b.note, "status": b.status, "seller": _who(b.seller),
                          "mine": viewer.is_authenticated and b.seller_id == viewer.pk, "when": b.created_at.isoformat(),
                          "order": getattr(getattr(b, "order", None), "id", None)} for b in bs]
    return d


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def projects(request):
    u = request.user
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in first.", 401)
        if not getattr(u, "is_email_verified", True):
            return _err("Verify your email before posting a project.", 403)
        d = request.data
        title, desc = _txt(d.get("title"), 120), _txt(d.get("description"), 4000)
        budget, days = _int(d.get("budget"), MIN_PRICE, MAX_PRICE), _int(d.get("days"), 1, 120)
        if len(title) < 8 or len(desc) < 30:
            return _err("Give a clear title (8+ letters) and explain the work (30+ letters).")
        if budget is None or days is None:
            return _err("Budget Rs %d to Rs %d, time 1 to 120 days." % (MIN_PRICE, MAX_PRICE))
        p = Project.objects.create(buyer=u, title=title, description=desc, budget=budget, days=days,
                                   category=d.get("category") if d.get("category") in CAT_KEYS else "other")
        return Response(_project(p, u, True))
    qs = Project.objects.filter(hidden=False).select_related("buyer")
    if request.GET.get("mine") and u.is_authenticated:
        qs = qs.filter(buyer=u)
    else:
        qs = qs.filter(status="open")
    if request.GET.get("cat") in CAT_KEYS:
        qs = qs.filter(category=request.GET["cat"])
    q = _txt(request.GET.get("q"), 60)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    return Response({"projects": [_project(p, u) for p in qs[:60]]})


@api_view(["GET"])
@permission_classes([AllowAny])
def project(request, pk):
    p = Project.objects.select_related("buyer").filter(pk=pk).first()
    if not p or (p.hidden and not _staff(request.user)):
        return _err("Project not found.", 404)
    return Response(_project(p, request.user, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def project_close(request, pk):
    p = Project.objects.filter(pk=pk, buyer=request.user).first()
    if not p:
        return _err("Project not found.", 404)
    if p.status == "open":
        p.status = "closed"; p.save(update_fields=["status"])
    return Response(_project(p, request.user, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bid(request, pk):
    u, d = request.user, request.data
    p = Project.objects.filter(pk=pk, status="open", hidden=False).first()
    if not p:
        return _err("This project is not open for bids.", 404)
    if p.buyer_id == u.pk:
        return _err("You cannot bid on your own project.")
    if not _kyc(u):
        return _err("Only members with a verified ID can bid. Get verified first.", 403)
    amount, days, note = _int(d.get("amount"), MIN_PRICE, MAX_PRICE), _int(d.get("days"), 1, 120), _txt(d.get("note"), 1500)
    if amount is None or days is None or len(note) < 20:
        return _err("Give your price (Rs %d or more), the days you need, and a short note on how you will do it (20+ letters)." % MIN_PRICE)
    b, made = Bid.objects.get_or_create(project=p, seller=u, defaults={"amount": amount, "days": days, "note": note})
    if not made:
        if b.status not in ("sent", "withdrawn"):
            return _err("Your bid was already answered.")
        b.amount, b.days, b.note, b.status = amount, days, note, "sent"; b.save()
    p.bids_count = p.bids.filter(status="sent").count(); p.save(update_fields=["bids_count"])
    if made:
        _notify(p.buyer, "%s sent a bid of Rs %s on \"%s\"" % (_name(u), "{:,}".format(amount), p.title[:60]), "/market#project-%d" % p.id)
    return Response(_project(p, u, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bid_act(request, pk, act):
    u = request.user
    b = Bid.objects.select_related("project", "seller").filter(pk=pk).first()
    if not b:
        return _err("Bid not found.", 404)
    p = b.project
    if act == "withdraw":
        if b.seller_id != u.pk or b.status != "sent":
            return _err("You can only withdraw your own open bid.", 403)
        b.status = "withdrawn"; b.save(update_fields=["status"])
    elif act == "accept":
        if p.buyer_id != u.pk or p.status != "open" or b.status != "sent":
            return _err("You can only accept an open bid on your own open project.", 403)
        if not _can_buy(u):
            return _err("Payments are not switched on yet.", 403)
        with transaction.atomic():
            Order.objects.filter(bid__project=p, status="pending").update(status="cancelled")   # only one accepted bid can be paid
            Order.objects.filter(bid=b).exclude(status="pending").filter(status="cancelled").update(bid=None)
            old = Order.objects.filter(bid=b).first()
            if old:
                return Response({"order": _order(old, u)})
            o = Order.objects.create(buyer=u, seller=b.seller, bid=b, title=p.title[:120], amount=b.amount, fee=_fee(b.amount),
                                     days=b.days, revisions_left=1, requirements=p.description[:3000])
        _sys(o, "Order made from the accepted bid. Pay to start the work.")
        return Response({"order": _order(o, u)})
    elif act == "reject":
        if p.buyer_id != u.pk or b.status != "sent":
            return _err("Not your project.", 403)
        b.status = "rejected"; b.save(update_fields=["status"])
    else:
        return _err("Unknown action.")
    p.bids_count = p.bids.filter(status="sent").count(); p.save(update_fields=["bids_count"])
    return Response(_project(p, u, True))


# ---------------------------------------------------------------- orders
def _fee(amount):
    return int(round(amount * FEE_PCT / 100.0))


def _order(o, viewer, full=False):
    role = "buyer" if viewer.pk == o.buyer_id else ("seller" if viewer.pk == o.seller_id else "team")
    d = {"id": o.id, "no": "XM-%06d" % o.id, "title": o.title, "amount": o.amount, "fee": o.fee, "seller_gets": o.amount - o.fee,
         "days": o.days, "status": o.status, "role": role, "buyer": _who(o.buyer), "seller": _who(o.seller), "gig": o.gig_id,
         "revisions_left": o.revisions_left, "created": o.created_at.isoformat(),
         "paid_at": o.paid_at.isoformat() if o.paid_at else "", "due_at": o.due_at.isoformat() if o.due_at else "",
         "delivered_at": o.delivered_at.isoformat() if o.delivered_at else "", "done_at": o.done_at.isoformat() if o.done_at else "",
         "auto_done": (o.delivered_at + timedelta(days=AUTO_DONE_DAYS)).isoformat() if (o.delivered_at and o.status == "delivered") else "",
         "test": o.provider in ("test",) or o.provider == "safepay-sandbox", "package": o.package,
         "refund_amount": o.refund_amount, "cancelled_by": o.cancelled_by, "unread": getattr(o, "unread", 0)}
    late = _hours_late(o)
    d["hours_late"], d["can_cancel_late"] = late, (role == "buyer" and late >= LATE_CANCEL_HOURS and o.status == "active")
    if full:
        ms = list(o.milestones.all())
        d["milestones"] = [_ms(m) for m in ms]
        if ms:
            d["released"] = sum(m.amount for m in ms if m.status == "accepted")
        d["files"] = [{"id": f.id, "kind": f.kind, "kind_label": dict(OrderFile.KINDS).get(f.kind, f.kind), "name": f.name, "size": f.size, "note": f.note,
                       "by": "me" if f.by_id == viewer.pk else _name(f.by), "mine": f.by_id == viewer.pk, "when": f.created_at.isoformat()}
                      for f in o.files.select_related("by")]
        cr = o.cancel_requests.filter(status="pending").first()
        d["cancel_request"] = ({"id": cr.id, "reason": cr.reason, "mine": cr.by_id == viewer.pk, "by": _name(cr.by),
                                "when": cr.created_at.isoformat(), "auto_at": (cr.created_at + timedelta(days=CANCEL_AUTO_DAYS)).isoformat()} if cr else None)
        d["can_request_cancel"] = role in ("buyer", "seller") and o.status in ("active", "delivered") and not cr
        d["offer"] = getattr(getattr(o, "offer", None), "id", None)
        d.update({"requirements": o.requirements, "delivery": o.delivery, "note": o.note,
                  "messages": [{"from": ("system" if m.sender_id is None else ("me" if m.sender_id == viewer.pk else _name(m.sender))),
                                "text": m.text, "when": m.created_at.isoformat()} for m in o.messages.select_related("sender")],
                  "review": ({"rating": o.review.rating, "text": o.review.text} if hasattr(o, "review") else None)})
    return d


def _mine(request, pk, staff_ok=True):
    o = Order.objects.select_related("buyer", "seller").filter(pk=pk).first()
    u = request.user
    if not o or not (u.pk in (o.buyer_id, o.seller_id) or (staff_ok and _staff(u))):
        return None
    return o


def _activate(o, provider_note=""):
    """Payment confirmed: the clock starts for the seller."""
    if o.status != "pending":
        return
    now = timezone.now()
    o.status, o.paid_at, o.due_at = "active", now, now + timedelta(days=o.days)
    if provider_note:
        o.note = provider_note[:300]
    o.save()
    if o.bid_id:
        Bid.objects.filter(pk=o.bid_id).update(status="accepted")
        Project.objects.filter(pk=o.bid.project_id).update(status="assigned")
    _sys(o, "Paid Rs %s. The seller has %d day%s to deliver." % ("{:,}".format(o.amount), o.days, "" if o.days == 1 else "s"))
    _notify(o.seller, "New paid order: %s (Rs %s)" % (o.title[:60], "{:,}".format(o.amount)), "/market#order-%d" % o.id)


def _settle(o, wait=0):
    """Ask Safepay whether a pending order was paid (amount must match)."""
    if o.status != "pending" or not o.provider.startswith("safepay-") or not o.provider_ref:
        return o.status != "pending"
    sv = _shop()
    import time
    for i in range(wait + 1):
        st, amt = sv.sp3_info(o.provider_ref)
        if st == "TRACKER_ENDED":
            if amt is not None and int(amt) != int(o.amount) * 100:
                o.note = ("amount mismatch: safepay %s, order %s" % (amt, o.amount * 100))[:300]; o.save(update_fields=["note"])
                return False
            _activate(o); return True
        if i < wait:
            time.sleep(2)
    return False


def _auto_complete(qs):
    cut = timezone.now() - timedelta(days=AUTO_DONE_DAYS)
    for o in qs.filter(status="delivered", delivered_at__lt=cut)[:50]:
        _complete(o, "Completed automatically %d days after delivery." % AUTO_DONE_DAYS)
    for m in Milestone.objects.filter(order__in=qs.filter(status="active"), status="delivered", delivered_at__lt=cut).select_related("order")[:50]:
        _ms_accept(m.order, m, "Milestone %d accepted automatically %d days after delivery." % (m.number, AUTO_DONE_DAYS))


def _complete(o, why):
    with transaction.atomic():
        o = Order.objects.select_for_update().get(pk=o.pk)
        if o.status not in ("delivered", "active", "disputed"):
            return o
        o.status, o.done_at = "completed", timezone.now()
        o.save(update_fields=["status", "done_at"])
        ms = list(Milestone.objects.select_for_update().filter(order=o))
        if ms:
            for m in ms:
                if m.status not in ("accepted", "cancelled"):
                    _release(o, m)
        else:
            try:
                Entry.objects.create(user_id=o.seller_id, amount=o.amount - o.fee, kind="earning", order=o,
                                     note="%s (Rs %s minus %d%% fee)" % (o.title[:80], "{:,}".format(o.amount), FEE_PCT))
            except IntegrityError:
                pass
        if o.gig_id:
            Gig.objects.filter(pk=o.gig_id).update(orders_done=Order.objects.filter(gig_id=o.gig_id, status="completed").count())
    _sys(o, why + " Rs %s added to the seller's balance." % "{:,}".format(o.amount - o.fee))
    _notify(o.seller, "Order completed: Rs %s added to your balance" % "{:,}".format(o.amount - o.fee), "/market#wallet")
    return o


def _start_pay(o, u):
    """Returns {'checkout': url} for Safepay, or {'simulate': True} in test mode without Safepay keys."""
    sv = _shop()
    if not _can_buy(u):
        return None, "Payments are not switched on yet."
    if sv.sp_ready():
        c = sv._sp3()
        try:
            d = sv._sp3_call("POST", "/order/payments/v3/", {"merchant_api_key": c["pub"], "intent": "CYBERSOURCE", "mode": "payment",
                                                            "entry_mode": "raw", "currency": "PKR", "amount": int(o.amount) * 100,
                                                            "metadata": {"market_order": str(o.id), "source": "xpertcreation"}, "include_fees": False})
            tracker = d["data"]["tracker"]["token"]
            tbt = sv._sp3_call("POST", "/client/passport/v1/token")["data"]
        except Exception as ex:
            o.note = ("could not start payment: %s" % ex)[:300]; o.save(update_fields=["note"])
            return None, "Could not start the payment. Please try again in a minute."
        o.provider, o.provider_ref = "safepay-" + c["env"], tracker
        o.save(update_fields=["provider", "provider_ref"])
        q = {"environment": c["env"], "tracker": tracker, "tbt": tbt, "source": "hosted",
             "redirect_url": SITE + "/api/market/pay/return/", "cancel_url": SITE + "/market?cancel=1#order-%d" % o.id}
        return {"checkout": c["checkout"] + "?" + urllib.parse.urlencode(q)}, None
    if _mode() == "test" and _staff(u):
        o.provider = "test"; o.save(update_fields=["provider"])
        return {"simulate": True}, None
    return None, "Payments are not switched on yet."


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def orders(request):
    u = request.user
    if request.method == "POST":
        d = request.data
        g = Gig.objects.filter(pk=_int(d.get("gig"), 1, 2 ** 62) or 0, active=True, hidden=False).select_related("seller").first()
        if not g:
            return _err("This gig is not available.", 404)
        if g.seller_id == u.pk:
            return _err("You cannot order your own gig.")
        if not _can_buy(u):
            return _err("Payments are not switched on yet.", 403)
        req = _txt(d.get("requirements"), 3000)
        if len(req) < 10:
            return _err("Tell the seller what you need (10+ letters).")
        tier, title, amount, days, revs = "", g.title, g.price, g.days, g.revisions
        if g.packages:
            p_ = next((x for x in g.packages if x.get("tier") == d.get("package")), None) or g.packages[0]
            tier, amount, days, revs = p_["tier"], p_["price"], p_["days"], p_["revisions"]
            title = ("%s (%s)" % (g.title, p_.get("name") or dict(TIERS).get(tier, tier)))[:120]
        o = Order.objects.create(buyer=u, seller=g.seller, gig=g, title=title, amount=amount, fee=_fee(amount), days=days,
                                 revisions_left=revs, requirements=req, package=tier)
        _sys(o, "Order placed. Pay to start the work.")
        pay, err = _start_pay(o, u)
        if err:
            return _err(err, 502 if "try again" in err else 403)
        return Response(dict(pay, order=_order(o, u)), status=201)
    qs = Order.objects.filter(Q(buyer=u) | Q(seller=u)).select_related("buyer", "seller")
    for o in qs.filter(status="pending", provider__startswith="safepay-", created_at__gte=timezone.now() - timedelta(hours=3))[:3]:
        _settle(o)
    _auto_complete(qs)
    qs = qs.exclude(status="cancelled", buyer=u, paid_at__isnull=True, created_at__lt=timezone.now() - timedelta(days=2))
    rows = _with_unread(qs[:100], u)
    return Response({"orders": [_order(o, u) for o in rows]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order(request, pk):
    o = _mine(request, pk)
    if not o:
        return _err("Order not found.", 404)
    if o.status == "pending":
        _settle(o)
    _auto_complete(Order.objects.filter(pk=o.pk))
    o.refresh_from_db()
    if request.user.pk == o.buyer_id:
        Order.objects.filter(pk=o.pk).update(buyer_seen=timezone.now())
    elif request.user.pk == o.seller_id:
        Order.objects.filter(pk=o.pk).update(seller_seen=timezone.now())
    return Response(_order(o, request.user, True))


def pay_return(request):
    d = request.POST if request.method == "POST" else request.GET
    tracker = (d.get("tracker") or "").strip()
    o = Order.objects.filter(provider_ref=tracker).first() if tracker.startswith("track_") else None
    if not o:
        return HttpResponseRedirect("/market?failed=1#orders")
    _settle(o, wait=3)
    return HttpResponseRedirect("/market?%s=1#order-%d" % ("paid" if o.status != "pending" else "failed", o.id))


pay_return = __import__("django.views.decorators.csrf", fromlist=["csrf_exempt"]).csrf_exempt(pay_return)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order_act(request, pk, act):
    u, d = request.user, request.data
    o = _mine(request, pk, staff_ok=False)
    if not o:
        return _err("Order not found.", 404)
    buyer, seller = u.pk == o.buyer_id, u.pk == o.seller_id
    text = _txt(d.get("text"), 3000)
    if act == "pay":
        if not buyer or o.status != "pending":
            return _err("Nothing to pay.")
        pay, err = _start_pay(o, u)
        return Response(pay) if pay else _err(err, 403)
    if act == "simulate":
        if not (buyer and o.status == "pending" and o.provider == "test" and _mode() == "test" and _staff(u)):
            return _err("Only staff, in test mode.", 403)
        o.provider_ref = "TEST-%d" % o.id; o.save(update_fields=["provider_ref"]); _activate(o)
    elif act == "msg":
        if not text:
            return _err("Write a message.")
        if o.status == "pending":
            return _err("Messages open once the order is paid.")
        Message.objects.create(order=o, sender=u, text=text)
        _notify(o.seller if buyer else o.buyer, "%s: %s" % (_name(u), text[:80]), "/market#order-%d" % o.id)
    elif act in ("deliver", "accept", "revision") and o.milestones.exists():
        return _err("This order is paid in milestones. Use the buttons on each milestone.")
    elif act == "deliver":
        if not seller or o.status != "active":
            return _err("Only the seller can deliver an order that is in progress.", 403)
        if len(text) < 5:
            return _err("Write what you delivered, with a link to the files (Google Drive, WeTransfer...).")
        o.status, o.delivery, o.delivered_at = "delivered", text, timezone.now(); o.save()
        _sys(o, "Delivered. The buyer has %d days to accept, ask for a revision or report a problem; after that it completes by itself." % AUTO_DONE_DAYS)
        Message.objects.create(order=o, sender=u, text="Delivery: " + text)
        _notify(o.buyer, "Your order was delivered: %s" % o.title[:60], "/market#order-%d" % o.id)
    elif act == "accept":
        if not buyer or o.status != "delivered":
            return _err("You can accept once the order is delivered.", 403)
        o = _complete(o, "The buyer accepted the delivery.")
    elif act == "revision":
        if not buyer or o.status != "delivered":
            return _err("You can ask for a revision once the order is delivered.", 403)
        if o.revisions_left < 1:
            return _err("No revisions left on this order. Accept it, or report a problem if the work is not what was agreed.")
        if len(text) < 10:
            return _err("Explain what should change (10+ letters).")
        o.status, o.revisions_left, o.delivered_at = "active", o.revisions_left - 1, None
        o.due_at = max(o.due_at or timezone.now(), timezone.now() + timedelta(days=2)); o.save()
        Message.objects.create(order=o, sender=u, text="Revision request: " + text)
        _notify(o.seller, "Revision requested: %s" % o.title[:60], "/market#order-%d" % o.id)
    elif act == "dispute":
        if not (buyer or seller) or o.status not in ("active", "delivered"):
            return _err("You can report a problem on an order that is in progress or delivered.", 403)
        if len(text) < 15:
            return _err("Explain the problem (15+ letters).")
        o.status, o.note = "disputed", ("Problem reported by %s: %s" % ("buyer" if buyer else "seller", text))[:300]; o.save()
        Message.objects.create(order=o, sender=u, text="Problem reported: " + text)
        _sys(o, "The XpertCreation team will look at this order and decide within 7 working days. Keep talking here.")
        try:
            from notifications.views import notify_admins
            notify_admins("market", "Marketplace problem on order XM-%06d" % o.id, "/market#admin")
        except Exception:
            pass
    elif act == "cancel":
        if buyer and o.status == "pending":
            o.status = "cancelled"; o.save(update_fields=["status"])
            _sys(o, "Cancelled before payment.")
        elif seller and o.status in ("active",):
            if len(text) < 10:
                return _err("Tell the buyer why you are declining (10+ letters).")
            _refund(o, "seller", "The seller declined the order: " + text)
        else:
            return _err("This order cannot be cancelled now. Report a problem instead.", 403)
    elif act == "cancel_late":
        if not buyer or o.status != "active":
            return _err("Only the buyer can do this, on an order in progress.", 403)
        late = _hours_late(o)
        if late < LATE_CANCEL_HOURS:
            return _err("You can cancel once the order is %d hours late (now %s)." % (LATE_CANCEL_HOURS, late))
        _refund(o, "late", "Cancelled by the buyer: the order was %s hours late." % late)
    elif act == "cancel_request":
        if o.status not in ("active", "delivered"):
            return _err("You can ask to cancel an order that is in progress or delivered.", 403)
        if o.cancel_requests.filter(status="pending").exists():
            return _err("There is already a cancel request waiting on this order.")
        if len(text) < 10:
            return _err("Explain why (10+ letters).")
        CancelRequest.objects.create(order=o, by=u, reason=text[:300])
        _sys(o, "%s asked to cancel: %s. The other side can agree or decline; with no reply in %d days it is agreed." % ("The buyer" if buyer else "The seller", text[:200], CANCEL_AUTO_DAYS))
        _notify(o.seller if buyer else o.buyer, "%s wants to cancel order XM-%06d. Reply within %d days." % (_name(u), o.id, CANCEL_AUTO_DAYS), "/market#order-%d" % o.id)
    elif act == "cancel_reply":
        cr = o.cancel_requests.filter(status="pending").first()
        what = d.get("answer")
        if not cr:
            return _err("No cancel request is waiting.")
        if what == "withdraw":
            if cr.by_id != u.pk:
                return _err("Only the person who asked can withdraw it.", 403)
            cr.status, cr.responded_at = "withdrawn", timezone.now(); cr.save()
            _sys(o, "The cancel request was withdrawn.")
        elif what in ("accept", "decline"):
            if cr.by_id == u.pk:
                return _err("The other side has to answer this.", 403)
            cr.status, cr.reply, cr.responded_at = ("accepted" if what == "accept" else "declined"), text[:300], timezone.now(); cr.save()
            if what == "accept":
                _refund(o, "both", "Both sides agreed to cancel: " + cr.reason)
            else:
                _sys(o, "The cancel request was declined." + (" " + text[:200] if text else "") + " If you cannot agree, report a problem and our team will decide.")
                _notify(cr.by, "Your cancel request on XM-%06d was declined." % o.id, "/market#order-%d" % o.id)
        else:
            return _err("Unknown answer.")
    elif act == "review":
        if not buyer or o.status != "completed":
            return _err("You can review once the order is completed.", 403)
        r = _int(d.get("rating"), 1, 5)
        if r is None:
            return _err("Pick 1 to 5 stars.")
        try:
            Review.objects.create(order=o, rating=r, text=_txt(d.get("text"), 500))
        except IntegrityError:
            return _err("You already reviewed this order.")
        if o.gig_id:
            agg = Review.objects.filter(order__gig_id=o.gig_id).aggregate(s=Sum("rating"))
            Gig.objects.filter(pk=o.gig_id).update(rating_sum=agg["s"] or 0, rating_n=Review.objects.filter(order__gig_id=o.gig_id).count())
    else:
        return _err("Unknown action.")
    o.refresh_from_db()
    return Response(_order(o, u, True))


# ---------------------------------------------------------------- seller balance and withdrawals
def _payout(p):
    return {"id": p.id, "amount": p.amount, "method": dict(Payout.METHODS).get(p.method, p.method), "account_name": p.account_name,
            "account_no": p.account_no, "bank": p.bank, "status": p.status, "reference": p.reference, "note": p.note,
            "when": p.created_at.isoformat(), "done": p.done_at.isoformat() if p.done_at else "", "user": _who(p.user)}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet(request):
    u = request.user
    _auto_complete(Order.objects.filter(seller=u))
    open_ = Order.objects.filter(seller=u, status__in=("active", "delivered", "disputed"))
    pending = open_.aggregate(s=Sum("amount"), f=Sum("fee"))
    released_ = Entry.objects.filter(user=u, kind="milestone", order__in=open_).aggregate(s=Sum("amount"))["s"] or 0
    return Response({"balance": _balance(u), "kyc": _kyc(u), "min": MIN_PAYOUT, "methods": Payout.METHODS,
                     "in_progress": (pending["s"] or 0) - (pending["f"] or 0) - released_,
                     "earned": Entry.objects.filter(user=u, kind__in=("earning", "milestone")).aggregate(s=Sum("amount"))["s"] or 0,
                     "entries": [{"amount": e.amount, "kind": e.kind, "note": e.note, "when": e.created_at.isoformat(), "order": e.order_id}
                                 for e in Entry.objects.filter(user=u)[:100]],
                     "payouts": [_payout(p) for p in Payout.objects.filter(user=u)[:50]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request):
    u, d = request.user, request.data
    if not _kyc(u):
        return _err("Withdrawals need a verified ID. Get verified first.", 403)
    method = d.get("method") if d.get("method") in dict(Payout.METHODS) else None
    name, acc, bank = _txt(d.get("account_name"), 80), re.sub(r"\s+", "", _txt(d.get("account_no"), 40)), _txt(d.get("bank"), 80)
    with transaction.atomic():
        from django.contrib.auth import get_user_model
        get_user_model().objects.select_for_update().get(pk=u.pk)      # one withdrawal at a time per member
        bal = _balance(u)
        amount = _int(d.get("amount"), MIN_PAYOUT, max(MIN_PAYOUT, bal))
        if bal < MIN_PAYOUT or amount is None:
            return _err("You can withdraw Rs %d to Rs %s." % (MIN_PAYOUT, "{:,}".format(bal)) if bal >= MIN_PAYOUT else
                        "The smallest withdrawal is Rs %d. Your balance is Rs %s." % (MIN_PAYOUT, "{:,}".format(bal)))
        if not method or len(name) < 3 or len(acc) < 10 or (method == "bank" and len(bank) < 3):
            return _err("Choose EasyPaisa, JazzCash or bank, and give the account title and number (and the bank name for a bank).")
        if Payout.objects.filter(user=u, status="requested").exists():
            return _err("You already have a withdrawal waiting. Wait until it is paid.")
        p = Payout.objects.create(user=u, amount=amount, method=method, account_name=name, account_no=acc, bank=bank)
        Entry.objects.create(user=u, amount=-amount, kind="payout", note="Withdrawal #%d to %s" % (p.id, dict(Payout.METHODS)[method]))
    try:
        from notifications.views import notify_admins
        notify_admins("market", "Marketplace withdrawal: Rs %s by %s" % ("{:,}".format(amount), _name(u)), "/market#admin")
    except Exception:
        pass
    return Response(_payout(p), status=201)


# ---------------------------------------------------------------- the team
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin(request):
    if not _staff(request.user):
        return _err("Team only.", 403)
    u = request.user
    return Response({"orders": [_order(o, u, True) for o in Order.objects.filter(status__in=("disputed", "refund_due")).select_related("buyer", "seller")[:50]],
                     "payouts": [_payout(p) for p in Payout.objects.filter(status="requested").select_related("user")[:100]],
                     "totals": {"orders": Order.objects.filter(status="completed").count(),
                                "sales": Order.objects.filter(status="completed").aggregate(s=Sum("amount"))["s"] or 0,
                                "fees": Order.objects.filter(status="completed").aggregate(s=Sum("fee"))["s"] or 0,
                                "owed": Entry.objects.aggregate(s=Sum("amount"))["s"] or 0}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_order(request, pk):
    if not _staff(request.user):
        return _err("Team only.", 403)
    o = Order.objects.filter(pk=pk).first()
    act, note = request.data.get("action"), _txt(request.data.get("note"), 200)
    if not o:
        return _err("Order not found.", 404)
    if act == "release" and o.status == "disputed":
        _complete(o, "The team decided for the seller." + (" " + note if note else ""))
    elif act == "refund" and o.status == "disputed":
        o.status = "refund_due"; o.note = ("Team: refund the buyer. " + note)[:300]; o.save(update_fields=["status", "note"])
        _sys(o, "The team decided for the buyer: a full refund to the original payment method within 7 to 14 working days.")
    elif act == "refunded" and o.status == "refund_due":
        o.status, o.done_at = "refunded", timezone.now(); o.note = ("Refunded. " + note)[:300]; o.save(update_fields=["status", "done_at", "note"])
        _sys(o, "Refund sent to the buyer." + (" Reference: " + note if note else ""))
        _notify(o.buyer, "Refund sent for order XM-%06d" % o.id, "/market#order-%d" % o.id)
    else:
        return _err("That action does not fit this order now.")
    o.refresh_from_db()
    return Response(_order(o, request.user, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_payout(request, pk):
    if not _staff(request.user):
        return _err("Team only.", 403)
    p = Payout.objects.filter(pk=pk, status="requested").first()
    act, ref, note = request.data.get("action"), _txt(request.data.get("reference"), 120), _txt(request.data.get("note"), 200)
    if not p:
        return _err("Withdrawal not found or already done.", 404)
    with transaction.atomic():
        if act == "paid":
            if len(ref) < 4:
                return _err("Enter the transaction ID of the payment you sent.")
            p.status, p.reference, p.note, p.done_at = "paid", ref, note, timezone.now(); p.save()
            _notify(p.user, "Your withdrawal of Rs %s was sent (ref %s)" % ("{:,}".format(p.amount), ref), "/market#wallet")
        elif act == "reject":
            if len(note) < 5:
                return _err("Write why, so the seller can fix it.")
            p.status, p.note, p.done_at = "rejected", note, timezone.now(); p.save()
            Entry.objects.create(user=p.user, amount=p.amount, kind="payout_back", note="Withdrawal #%d returned: %s" % (p.id, note))
            _notify(p.user, "Your withdrawal was not sent: %s. The money is back in your balance." % note, "/market#wallet")
        else:
            return _err("Unknown action.")
    return Response(_payout(p))



# ---------------------------------------------------------------- gig pictures (up to 3, cropped to 3:2 webp)
from rest_framework.decorators import parser_classes                                   # noqa: E402
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser             # noqa: E402

MAX_PICS, MAX_PIC_MB = 3, 6


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def gig_image(request, pk):
    import os
    import secrets
    from django.conf import settings
    g = Gig.objects.filter(pk=pk, seller=request.user).first()
    if not g:
        return _err("Only the seller can change the pictures.", 403)
    pics = list(g.images or [])
    if request.data.get("remove") is not None:
        i = _int(request.data.get("remove"), 0, 10)
        if i is not None and i < len(pics):
            old = pics.pop(i)
            try:
                os.remove(os.path.join(str(settings.MEDIA_ROOT), old))
            except OSError:
                pass
        g.images = pics; g.save(update_fields=["images"])
        return Response(_gig(g, True))
    if request.data.get("first") is not None:
        i = _int(request.data.get("first"), 0, 10)
        if i is not None and i < len(pics):
            pics.insert(0, pics.pop(i)); g.images = pics; g.save(update_fields=["images"])
        return Response(_gig(g, True))
    f = request.FILES.get("file")
    if not f:
        return _err("Choose a picture.")
    if len(pics) >= MAX_PICS:
        return _err("A service can have %d pictures. Remove one first." % MAX_PICS)
    if f.size > MAX_PIC_MB * 1024 * 1024:
        return _err("The picture is over %d MB." % MAX_PIC_MB)
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); im.load()
    except Exception:
        return _err("That file is not a picture we can read.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im = ImageOps.fit(im, (1200, 800), Image.LANCZOS)
    rel = os.path.join("market", timezone.localdate().strftime("%Y%m"), "%d_%s.webp" % (g.id, secrets.token_hex(6)))
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=82)
    g.images = pics + [rel]; g.save(update_fields=["images"])
    return Response(_gig(g, True))


@api_view(["GET"])
@permission_classes([AllowAny])
def seller(request, username):
    from django.contrib.auth import get_user_model
    u = get_user_model().objects.filter(username__iexact=username[:30], is_active=True).first()
    if not u:
        return _err("Seller not found.", 404)
    gs = Gig.objects.filter(seller=u, active=True, hidden=False).select_related("seller")
    st = _seller_stats(u.pk)
    revs = [{"rating": r.rating, "text": r.text, "by": _name(r.order.buyer), "when": r.created_at.isoformat(), "gig": r.order.title}
            for r in Review.objects.filter(order__seller=u).select_related("order__buyer").order_by("-id")[:20]]
    return Response({"seller": _who(u), "stats": st, "since": getattr(u, "date_joined", timezone.now()).isoformat(), "kyc": _kyc(u),
                     "cv": CV.objects.filter(user=u, public=True).exists(),
                     "gigs": [dict(_gig(g), level=st["level"]) for g in gs], "reviews": revs})


# ================================================================ v5: packages, custom offers, milestones, files, cancel rules, deadlines, CV
def _hours_late(o):
    if o.status != "active" or not o.due_at:
        return 0
    s = (timezone.now() - o.due_at).total_seconds() / 3600.0
    return round(s, 1) if s > 0 else 0


def _with_unread(qs, u):
    """Adds .unread: messages from the other side (or the system) after this member last opened the order."""
    from datetime import datetime, timezone as _tz
    return _unread_py(qs, u, datetime(2000, 1, 1, tzinfo=_tz.utc))


def _unread_py(qs, u, old):
    rows = list(qs)
    ids = [o.id for o in rows]
    msgs = Message.objects.filter(order_id__in=ids).values_list("order_id", "sender_id", "created_at")
    by = {}
    for oid, sid, at in msgs:
        by.setdefault(oid, []).append((sid, at))
    for o in rows:
        seen = (o.buyer_seen if u.pk == o.buyer_id else o.seller_seen) or old
        o.unread = sum(1 for sid, at in by.get(o.id, []) if sid != u.pk and at > seen)
    return rows


def _ms(m):
    late = m.status in ("working", "revision") and m.due_at and timezone.now() > m.due_at
    return {"id": m.id, "number": m.number, "title": m.title, "amount": m.amount, "days": m.days, "status": m.status,
            "delivery": m.delivery, "revision_note": m.revision_note, "fee": m.fee, "late": bool(late),
            "due_at": m.due_at.isoformat() if m.due_at else "", "delivered_at": m.delivered_at.isoformat() if m.delivered_at else "",
            "accepted_at": m.accepted_at.isoformat() if m.accepted_at else "",
            "auto_at": (m.delivered_at + timedelta(days=AUTO_DONE_DAYS)).isoformat() if (m.delivered_at and m.status == "delivered") else ""}


def _release(o, m):
    """Pay one milestone to the seller's balance (minus the fee). Safe to call twice."""
    if m.status == "accepted":
        return
    m.fee = _fee(m.amount)
    m.status, m.accepted_at = "accepted", timezone.now()
    m.save(update_fields=["fee", "status", "accepted_at"])
    Entry.objects.create(user_id=o.seller_id, amount=m.amount - m.fee, kind="milestone", order=o,
                         note="%s, milestone %d: %s (Rs %s minus %d%% fee)" % (o.title[:60], m.number, m.title[:50], "{:,}".format(m.amount), FEE_PCT))


def _ms_accept(o, m, why):
    with transaction.atomic():
        m = Milestone.objects.select_for_update().get(pk=m.pk)
        if m.status != "delivered" or o.status != "active":
            return
        _release(o, m)
    _sys(o, why + " Rs %s added to the seller's balance." % "{:,}".format(m.amount - m.fee))
    _notify(o.seller, "Milestone %d accepted on XM-%06d: Rs %s added to your balance" % (m.number, o.id, "{:,}".format(m.amount - m.fee)), "/market#order-%d" % o.id)
    if not o.milestones.exclude(status__in=("accepted", "cancelled")).exists():
        _complete(o, "All milestones are done.")


def _refund(o, by, why):
    """Cancel a paid order: the buyer gets back what was not released to the seller (the team sends it through Safepay)."""
    released = sum(m.amount for m in o.milestones.filter(status="accepted"))
    o.milestones.exclude(status="accepted").update(status="cancelled")
    o.refund_amount = max(0, o.amount - released)
    o.status, o.cancelled_by = "refund_due", by
    o.note = (why + (" Rs %s already paid for finished milestones stays with the seller." % "{:,}".format(released) if released else ""))[:300]
    o.save(update_fields=["refund_amount", "status", "cancelled_by", "note"])
    _sys(o, why[:250] + " The buyer gets Rs %s back to the original payment method within 7 to 14 working days." % "{:,}".format(o.refund_amount))
    for x in (o.buyer, o.seller):
        _notify(x, "Order XM-%06d cancelled. Refund to the buyer: Rs %s" % (o.id, "{:,}".format(o.refund_amount)), "/market#order-%d" % o.id)
    if o.bid_id:
        Project.objects.filter(pk=o.bid.project_id, status="assigned").update(status="open")
    try:
        from notifications.views import notify_admins
        notify_admins("market", "Refund due on marketplace order XM-%06d (Rs %s)" % (o.id, "{:,}".format(o.refund_amount)), "/market#admin")
    except Exception:
        pass


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def milestone_act(request, pk, act):
    u, d = request.user, request.data
    m = Milestone.objects.select_related("order", "order__buyer", "order__seller").filter(pk=pk).first()
    if not m or u.pk not in (m.order.buyer_id, m.order.seller_id):
        return _err("Milestone not found.", 404)
    o = m.order
    seller, buyer = u.pk == o.seller_id, u.pk == o.buyer_id
    text = _txt(d.get("text"), 3000)
    if o.status != "active":
        return _err("Milestones are worked on while the order is in progress.")
    if act == "start":
        if not seller or m.status not in ("waiting",):
            return _err("Only the seller can start a waiting milestone.", 403)
        m.status, m.started_at, m.due_at = "working", timezone.now(), timezone.now() + timedelta(days=m.days)
        m.save(update_fields=["status", "started_at", "due_at"])
        _sys(o, "Milestone %d started: %s (due in %d days)." % (m.number, m.title, m.days))
        _notify(o.buyer, "Work started on milestone %d of XM-%06d" % (m.number, o.id), "/market#order-%d" % o.id)
    elif act == "deliver":
        if not seller or m.status not in ("waiting", "working", "revision"):
            return _err("Only the seller can deliver this milestone now.", 403)
        if len(text) < 5:
            return _err("Write what you delivered, with a link to the files or upload them below.")
        m.status, m.delivery, m.delivered_at = "delivered", text, timezone.now()
        m.save(update_fields=["status", "delivery", "delivered_at"])
        Message.objects.create(order=o, sender=u, text="Milestone %d delivered: %s" % (m.number, text))
        _sys(o, "The buyer has %d days to accept milestone %d or ask for changes; after that it is accepted by itself." % (AUTO_DONE_DAYS, m.number))
        _notify(o.buyer, "Milestone %d delivered on XM-%06d - please check it" % (m.number, o.id), "/market#order-%d" % o.id)
    elif act == "accept":
        if not buyer or m.status != "delivered":
            return _err("You can accept a milestone once it is delivered.", 403)
        _ms_accept(o, m, "The buyer accepted milestone %d." % m.number)
    elif act == "revision":
        if not buyer or m.status != "delivered":
            return _err("You can ask for changes once a milestone is delivered.", 403)
        if len(text) < 10:
            return _err("Explain what should change (10+ letters).")
        m.status, m.revision_note, m.due_at = "revision", text, max(m.due_at or timezone.now(), timezone.now() + timedelta(days=2))
        m.save(update_fields=["status", "revision_note", "due_at"])
        Message.objects.create(order=o, sender=u, text="Changes asked on milestone %d: %s" % (m.number, text))
        _notify(o.seller, "Changes asked on milestone %d of XM-%06d" % (m.number, o.id), "/market#order-%d" % o.id)
    else:
        return _err("Unknown action.")
    o.refresh_from_db()
    return Response(_order(o, u, True))


# ---------------- custom requests and offers
def _offer(x, viewer):
    live = x.status == "pending" and x.expires_at > timezone.now()
    return {"id": x.id, "title": x.title, "description": x.description, "price": x.price, "days": x.days, "revisions": x.revisions,
            "milestones": x.milestones or [], "status": ("expired" if x.status == "pending" and not live else x.status), "live": live,
            "seller": _who(x.seller), "buyer": _who(x.buyer), "gig": x.gig_id, "gig_title": x.gig.title if x.gig_id and x.gig else "",
            "request": x.request_id, "order": x.order_id, "expires": x.expires_at.isoformat(), "when": x.created_at.isoformat(),
            "mine": x.seller_id == viewer.pk}


def _request(r, viewer):
    return {"id": r.id, "brief": r.brief, "budget": r.budget, "days": r.days, "status": r.status, "buyer": _who(r.buyer), "seller": _who(r.seller),
            "gig": r.gig_id, "gig_title": r.gig.title if r.gig_id and r.gig else "", "when": r.created_at.isoformat(),
            "offers": [_offer(x, viewer) for x in r.offers.select_related("seller", "buyer", "gig")]}


def _user(username):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(username__iexact=str(username or "")[:30], is_active=True).first()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def requests_(request):
    u = request.user
    if request.method == "GET":
        CustomOffer.objects.filter(status="pending", expires_at__lt=timezone.now()).update(status="expired")
        rel = ("buyer", "seller", "gig")
        return Response({"requests_in": [_request(r, u) for r in CustomRequest.objects.filter(seller=u).select_related(*rel)[:50]],
                         "requests_out": [_request(r, u) for r in CustomRequest.objects.filter(buyer=u).select_related(*rel)[:50]],
                         "offers_in": [_offer(x, u) for x in CustomOffer.objects.filter(buyer=u).select_related(*rel)[:50]],
                         "offers_out": [_offer(x, u) for x in CustomOffer.objects.filter(seller=u).select_related(*rel)[:50]]})
    d = request.data
    s = _user(d.get("seller"))
    if not s:
        return _err("Seller not found.", 404)
    if s.pk == u.pk:
        return _err("You cannot send a request to yourself.")
    if not _kyc(s):
        return _err("This member is not selling yet.")
    brief = _txt(d.get("brief"), 3000)
    if len(brief) < 20:
        return _err("Describe the work in a little more detail (20+ letters).")
    if CustomRequest.objects.filter(buyer=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= 10:
        return _err("You sent many requests today. Please wait for answers.", 429)
    g = Gig.objects.filter(pk=_int(d.get("gig"), 1, 2 ** 62) or 0, seller=s).first()
    r = CustomRequest.objects.create(buyer=u, seller=s, gig=g, brief=brief, budget=_int(d.get("budget"), 0, MAX_PRICE) or 0, days=_int(d.get("days"), 0, 365) or 0)
    _notify(s, "%s asked you for a custom offer%s" % (_name(u), (" (budget Rs %s)" % "{:,}".format(r.budget)) if r.budget else ""), "/market#offers")
    return Response(_request(r, u), status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_close(request, pk):
    r = CustomRequest.objects.filter(pk=pk).filter(Q(buyer=request.user) | Q(seller=request.user)).first()
    if not r:
        return _err("Request not found.", 404)
    if r.status in ("open", "offered"):
        r.status = "declined" if request.user.pk == r.seller_id else "closed"; r.save(update_fields=["status"])
        if request.user.pk == r.seller_id:
            _notify(r.buyer, "%s cannot take your custom request." % _name(request.user), "/market#offers")
    return Response(_request(r, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offers(request):
    u, d = request.user, request.data
    if not _kyc(u):
        return _err("Only members with a verified ID can send offers. Get verified first.", 403)
    req = None
    if d.get("request"):
        req = CustomRequest.objects.filter(pk=_int(d.get("request"), 1, 2 ** 62) or 0, seller=u).first()
        if not req:
            return _err("Request not found.", 404)
        buyer, gig = req.buyer, req.gig
    else:
        buyer = _user(d.get("buyer"))
        if not buyer:
            return _err("Buyer not found. Use their username.", 404)
        gig = Gig.objects.filter(pk=_int(d.get("gig"), 1, 2 ** 62) or 0, seller=u).first()
    if buyer.pk == u.pk:
        return _err("You cannot send an offer to yourself.")
    title, desc = _txt(d.get("title"), 120), _txt(d.get("description"), 3000)
    price, days, revs = _int(d.get("price"), MIN_PRICE, MAX_PRICE), _int(d.get("days"), 1, 365), _int(d.get("revisions"), 0, 10)
    if len(title) < 5 or len(desc) < 20:
        return _err("Give a clear title and say what the buyer gets (20+ letters).")
    if price is None or days is None or revs is None:
        return _err("Price Rs %d to Rs %s, 1 to 365 days, 0 to 10 revisions." % (MIN_PRICE, "{:,}".format(MAX_PRICE)))
    ms = []
    for x in (d.get("milestones") or [])[:12]:
        if not isinstance(x, dict):
            continue
        a_, t_, dd = _int(x.get("amount"), 100, MAX_PRICE), _txt(x.get("title"), 120), _int(x.get("days"), 1, 365)
        if a_ is None or len(t_) < 3 or dd is None:
            return _err("Each milestone needs a title, an amount (Rs 100 or more) and days.")
        ms.append({"title": t_, "amount": a_, "days": dd})
    if len(ms) == 1:
        return _err("Use at least two milestones, or none.")
    if ms and sum(x["amount"] for x in ms) != price:
        return _err("The milestones add up to Rs %s but the price is Rs %s." % ("{:,}".format(sum(x["amount"] for x in ms)), "{:,}".format(price)))
    if ms:
        days = max(days, sum(x["days"] for x in ms))
    x = CustomOffer.objects.create(request=req, seller=u, buyer=buyer, gig=gig, title=title, description=desc, price=price, days=days,
                                   revisions=revs, milestones=ms, expires_at=timezone.now() + timedelta(days=OFFER_DAYS))
    if req:
        req.status = "offered"; req.save(update_fields=["status"])
    _notify(buyer, "Custom offer from %s: Rs %s, %d days" % (_name(u), "{:,}".format(price), days), "/market#offers")
    return Response(_offer(x, u), status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offer_act(request, pk, act):
    u = request.user
    x = CustomOffer.objects.select_related("seller", "buyer", "gig", "request").filter(pk=pk).first()
    if not x or u.pk not in (x.seller_id, x.buyer_id):
        return _err("Offer not found.", 404)
    if act == "withdraw":
        if u.pk != x.seller_id or x.status != "pending":
            return _err("You can withdraw your own open offer.", 403)
        x.status, x.responded_at = "withdrawn", timezone.now(); x.save(update_fields=["status", "responded_at"])
        if x.request_id:
            CustomRequest.objects.filter(pk=x.request_id).update(status="open")
        return Response(_offer(x, u))
    if u.pk != x.buyer_id:
        return _err("Only the buyer can answer this offer.", 403)
    if act == "decline":
        if x.status != "pending":
            return _err("This offer was already answered.")
        x.status, x.responded_at = "declined", timezone.now(); x.save(update_fields=["status", "responded_at"])
        if x.request_id:
            CustomRequest.objects.filter(pk=x.request_id).update(status="declined")
        _notify(x.seller, "%s declined your custom offer." % _name(u), "/market#offers")
        return Response(_offer(x, u))
    if act != "accept":
        return _err("Unknown action.")
    if x.order_id:
        o = x.order
        if o.status == "pending":
            pay, err = _start_pay(o, u)
            return Response(dict(pay, order=_order(o, u))) if pay else _err(err, 403)
        return Response({"order": _order(o, u)})
    if x.status != "pending" or x.expires_at < timezone.now():
        return _err("This offer is no longer open.")
    if not _can_buy(u):
        return _err("Payments are not switched on yet.", 403)
    with transaction.atomic():
        o = Order.objects.create(buyer=u, seller=x.seller, gig=x.gig, title=x.title, amount=x.price, fee=_fee(x.price), days=x.days,
                                 revisions_left=x.revisions, requirements=(x.request.brief + "\n\nOffer: " if x.request_id else "") + x.description,
                                 package="custom")
        for i, mm in enumerate(x.milestones or [], start=1):
            Milestone.objects.create(order=o, number=i, title=mm["title"], amount=mm["amount"], days=mm["days"])
        x.status, x.order, x.responded_at = "accepted", o, timezone.now(); x.save(update_fields=["status", "order", "responded_at"])
        if x.request_id:
            CustomRequest.objects.filter(pk=x.request_id).update(status="accepted")
    _sys(o, "Order made from a custom offer%s. Pay to start the work." % (" with %d milestones" % len(x.milestones) if x.milestones else ""))
    _notify(x.seller, "%s accepted your custom offer (Rs %s). Work starts after payment." % (_name(u), "{:,}".format(x.price)), "/market#order-%d" % o.id)
    pay, err = _start_pay(o, u)
    if err:
        return _err(err, 403)
    return Response(dict(pay, order=_order(o, u)), status=201)


# ---------------- files on an order (kept outside the website)
def _files_dir():
    import os
    try:
        from companies.views import DOCS
        base = os.path.dirname(DOCS.rstrip("/"))
    except Exception:
        base = "/var/lib/gunicorn-academy"
    return os.environ.get("XC_MARKET_FILES", os.path.join(base, "market_files"))


from rest_framework.decorators import parser_classes as _pc                            # noqa: E402
from rest_framework.parsers import FormParser as _FP, JSONParser as _JP, MultiPartParser as _MP  # noqa: E402


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@_pc([_MP, _FP, _JP])
def order_files(request, pk):
    import os
    import secrets
    o = _mine(request, pk, staff_ok=False)
    if not o:
        return _err("Order not found.", 404)
    if o.status in ("pending", "cancelled", "refunded"):
        return _err("Files can be added once the order is paid.")
    f = request.FILES.get("file")
    if not f:
        return _err("Choose a file.")
    name = re.sub(r"[^\w.\- ()]+", "_", f.name or "file")[:150]
    ext = os.path.splitext(name)[1].lower()
    if ext not in FILE_EXT:
        return _err("This file type is not allowed. Use images, PDF, Office files, ZIP, audio or video.")
    if f.size > MAX_FILE_MB * 1024 * 1024:
        return _err("The file is over %d MB. For bigger files share a Google Drive or WeTransfer link in the messages." % MAX_FILE_MB)
    if o.files.count() >= MAX_FILES:
        return _err("An order can have %d files." % MAX_FILES)
    rel = "o%d/%s%s" % (o.id, secrets.token_hex(12), ext)
    full = os.path.join(_files_dir(), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as out:
        for ch in f.chunks():
            out.write(ch)
    os.chmod(full, 0o600)
    seller = request.user.pk == o.seller_id
    kind = request.data.get("kind") if request.data.get("kind") in dict(OrderFile.KINDS) else ("delivery" if seller else "brief")
    x = OrderFile.objects.create(order=o, by=request.user, kind=kind, path=rel, name=name, size=f.size, note=_txt(request.data.get("note"), 200))
    _sys(o, "%s added a file: %s (%s)." % ("The seller" if seller else "The buyer", name, dict(OrderFile.KINDS)[kind].lower()))
    _notify(o.buyer if seller else o.seller, "%s added a file on XM-%06d: %s" % (_name(request.user), o.id, name[:60]), "/market#order-%d" % o.id)
    return Response(_order(o, request.user, True))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def order_file(request, pk):
    import os
    from django.http import FileResponse, Http404
    x = OrderFile.objects.select_related("order").filter(pk=pk).first()
    u = request.user
    if not x or not (u.pk in (x.order.buyer_id, x.order.seller_id) or _staff(u)):
        raise Http404
    full = os.path.join(_files_dir(), x.path)
    if request.method == "POST":                     # remove: the person who added it, while the order is not finished
        if x.by_id != u.pk or x.order.status in ("completed", "refunded"):
            return _err("You can remove your own files while the order is open.", 403)
        try:
            os.remove(full)
        except OSError:
            pass
        x.delete()
        return Response(_order(x.order, u, True))
    if not os.path.exists(full):
        raise Http404
    r = FileResponse(open(full, "rb"), as_attachment=True, filename=x.name)
    r["X-Content-Type-Options"] = "nosniff"; r["Cache-Control"] = "private, no-store"
    return r


# ---------------- public order tracking (no names of the buyer)
@api_view(["GET"])
@permission_classes([AllowAny])
def track(request, no):
    m = re.match(r"^(?:XM-?)?0*(\d{1,9})$", str(no).strip().upper())
    o = Order.objects.select_related("seller").filter(pk=int(m.group(1))).first() if m else None
    if not o or o.status == "cancelled":
        return _err("No order with that number.", 404)
    ms = list(o.milestones.all())
    return Response({"no": "XM-%06d" % o.id, "title": o.title, "status": o.status, "seller": _name(o.seller).split(" ")[0],
                     "created": o.created_at.isoformat(), "paid": o.paid_at.isoformat() if o.paid_at else "",
                     "due": o.due_at.isoformat() if o.due_at else "", "delivered": o.delivered_at.isoformat() if o.delivered_at else "",
                     "done": o.done_at.isoformat() if o.done_at else "",
                     "milestones": [{"number": x.number, "title": x.title, "status": x.status} for x in ms]})


# ---------------- CV / resume builder
CV_FIELDS = {"name": 80, "headline": 120, "email": 120, "phone": 40, "city": 80, "country": 60, "website": 160, "summary": 1500,
             "skills": 600, "languages": 300}
CV_LISTS = {"experience": ("title", "org", "start", "end", "detail"), "education": ("title", "org", "start", "end", "detail"),
            "certifications": ("title", "org", "start", "end", "detail"), "projects": ("title", "org", "start", "end", "detail")}


def _cv_clean(d):
    out = {k: _txt(d.get(k), n) for k, n in CV_FIELDS.items()}
    for k, keys in CV_LISTS.items():
        rows = []
        for r in (d.get(k) or [])[:15]:
            if isinstance(r, dict):
                row = {f: _txt(r.get(f), 1200 if f == "detail" else 120) for f in keys}
                if row["title"]:
                    rows.append(row)
        out[k] = rows
    return out


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def cv(request):
    u = request.user
    c = CV.objects.filter(user=u).first()
    if request.method == "POST":
        c = c or CV(user=u)
        c.data = _cv_clean(request.data.get("data") or {})
        c.template = request.data.get("template") if request.data.get("template") in ("classic", "modern", "minimal") else "classic"
        c.public = bool(request.data.get("public"))
        c.save()
    prof = _cv_from_profile(u)
    if not c:
        d = {"name": _name(u), "email": u.email or "", "phone": getattr(u, "whatsapp", "") or getattr(u, "phone", "") or "",
             "certifications": [], "projects": [], "languages": ""}
        d.update(prof)
        return Response({"exists": False, "template": "classic", "public": False, "username": u.username, "data": d, "profile": prof})
    return Response({"exists": True, "template": c.template, "public": c.public, "data": c.data, "username": u.username, "updated": c.updated_at.isoformat(),
                     "profile": prof})


_MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_CTRY = {"PK": "Pakistan", "AE": "UAE", "SA": "Saudi Arabia", "GB": "United Kingdom", "US": "USA", "CA": "Canada", "QA": "Qatar", "OM": "Oman",
         "KW": "Kuwait", "BH": "Bahrain", "IN": "India", "BD": "Bangladesh", "AU": "Australia", "DE": "Germany", "MY": "Malaysia", "TR": "Turkey", "CN": "China"}


def _cv_when(m, y):
    return ("%s %s" % (_MON[m], y) if m and 0 < m < 13 else str(y)) if y else ""


def _cv_from_profile(u):
    """Experience, education, skills and contact from the member's profile (network app), in CV form."""
    out = {"headline": "", "summary": "", "city": "", "country": "", "website": "", "skills": "", "experience": [], "education": []}
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).first()
    except Exception:
        p = None
    if not p:
        return out
    out.update({"headline": p.headline or "", "summary": p.about or "", "city": p.city or "",
                "country": _CTRY.get((p.country or "").upper(), p.country or ""), "website": p.website or ""})
    import logging
    log = logging.getLogger("market.cv")
    try:                                    # skills: most endorsed first (same order as on the profile)
        from django.db.models import Count as _C
        out["skills"] = ", ".join(s.name for s in p.skills.annotate(n=_C("endorsements")).order_by("-n", "order", "id"))[:600]
    except Exception:
        log.exception("cv skills")
        try:
            out["skills"] = ", ".join(s.name for s in p.skills.all())[:600]
        except Exception:
            pass
    try:
        exp = sorted(p.experience.all(), key=lambda x: (x.end_year is not None, -(x.start_year or 0), -(x.start_month or 0)))
        out["experience"] = [{"title": x.title or "", "org": ", ".join(v for v in (x.company, x.city) if v), "start": _cv_when(x.start_month, x.start_year),
                              "end": "Now" if x.end_year is None else _cv_when(x.end_month, x.end_year), "detail": x.description or ""} for x in exp][:15]
    except Exception:
        log.exception("cv experience")
    try:
        out["education"] = [{"title": ", ".join(v for v in (x.degree, x.field) if v) or x.school, "org": x.school if (x.degree or x.field) else "",
                             "start": str(x.start_year or ""), "end": str(x.end_year or ""), "detail": ""} for x in p.education.all()][:15]
    except Exception:
        log.exception("cv education")
    return out


@api_view(["GET"])
@permission_classes([AllowAny])
def cv_public(request, username):
    owner = _user(username)
    c = CV.objects.filter(user=owner).first() if owner else None
    if not c or not (c.public or (request.user.is_authenticated and (request.user.pk == owner.pk or _staff(request.user)))):
        return _err("This CV is not public.", 404)
    d = dict(c.data)
    if not (request.user.is_authenticated and request.user.pk == owner.pk):
        d.pop("phone", None)                          # contact stays private on the public view
    return Response({"template": c.template, "data": d, "username": owner.username, "avatar": _avatar(owner), "kyc": _kyc(owner)})


# ---------------- the clock: run every 30 minutes (cron) - deadlines, auto-accept, expiries
def tick():
    now = timezone.now()
    n = {"auto": 0, "reminded": 0, "late": 0, "cancel_auto": 0, "expired": 0, "unpaid": 0}
    _auto_complete(Order.objects.all())
    for o in Order.objects.filter(status="active", reminded=False, due_at__gt=now, due_at__lte=now + timedelta(hours=24)).select_related("seller")[:200]:
        _notify(o.seller, "XM-%06d is due in less than 24 hours. Please deliver on time." % o.id, "/market#order-%d" % o.id)
        Order.objects.filter(pk=o.pk).update(reminded=True); n["reminded"] += 1
    for o in Order.objects.filter(status="active", late_noted=False, due_at__lt=now).select_related("seller", "buyer")[:200]:
        _notify(o.seller, "XM-%06d is late. Please deliver as soon as you can." % o.id, "/market#order-%d" % o.id)
        _notify(o.buyer, "XM-%06d is late. If it is still not delivered %d hours after the due time, you can cancel it for a refund." % (o.id, LATE_CANCEL_HOURS), "/market#order-%d" % o.id)
        _sys(o, "This order is past its delivery time.")
        Order.objects.filter(pk=o.pk).update(late_noted=True); n["late"] += 1
    for cr in CancelRequest.objects.filter(status="pending", created_at__lt=now - timedelta(days=CANCEL_AUTO_DAYS)).select_related("order", "order__buyer", "order__seller")[:100]:
        cr.status, cr.responded_at = "auto", now; cr.save(update_fields=["status", "responded_at"])
        if cr.order.status in ("active", "delivered"):
            _refund(cr.order, "both", "No reply to the cancel request in %d days, so it was agreed: %s" % (CANCEL_AUTO_DAYS, cr.reason))
        n["cancel_auto"] += 1
    n["expired"] = CustomOffer.objects.filter(status="pending", expires_at__lt=now).update(status="expired")
    for o in Order.objects.filter(status="pending", created_at__lt=now - timedelta(hours=PENDING_HOURS))[:200]:
        if o.provider.startswith("safepay-") and _settle(o):
            continue
        Order.objects.filter(pk=o.pk, status="pending").update(status="cancelled"); n["unpaid"] += 1
        CustomOffer.objects.filter(order=o, status="accepted").update(status="expired")
    return n
