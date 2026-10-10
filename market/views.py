"""Freelance marketplace API (/api/market/). See models.py for the flow."""
import re
import urllib.parse
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CATS, Bid, Entry, Gig, Message, Order, Payout, Project, Review

FEE_PCT = 10                     # XpertCreation keeps 10% of every order, from the seller's side
AUTO_DONE_DAYS = 3               # a delivered order completes by itself after this many days
MIN_PAYOUT = 500
MIN_PRICE, MAX_PRICE = 500, 500000
SITE = "https://xpertcreation.com"
CAT_KEYS = dict(CATS)


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _kyc(u):
    k = getattr(u, "person_kyc", None)
    try:
        return bool(k and k.status == "approved")
    except Exception:
        return False


def _name(u):
    return ((getattr(u, "full_name", "") or u.username or "Member #%d" % u.pk) if u else "Deleted member")[:60]


def _who(u):
    return {"id": u.pk, "name": _name(u), "username": u.username or ""} if u else {"id": 0, "name": "Deleted member", "username": ""}


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


def _sys(o, text):
    Message.objects.create(order=o, sender=None, text=text)


# ---------------------------------------------------------------- listings
def _gig(g, full=False):
    d = {"id": g.id, "title": g.title, "category": g.category, "cat": CAT_KEYS.get(g.category, ""), "price": g.price, "days": g.days,
         "revisions": g.revisions, "active": g.active and not g.hidden, "orders": g.orders_done,
         "rating": round(g.rating_sum / g.rating_n, 1) if g.rating_n else None, "ratings": g.rating_n, "seller": _who(g.seller),
         "summary": g.description[:160]}
    if full:
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
        me = {"id": u.pk, "name": _name(u), "kyc": _kyc(u), "staff": _staff(u), "balance": _balance(u), "can_buy": _can_buy(u)}
    return Response({"cats": CATS, "fee_pct": FEE_PCT, "mode": _mode(), "min_price": MIN_PRICE, "min_payout": MIN_PAYOUT,
                     "auto_days": AUTO_DONE_DAYS, "me": me})


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
    return Response({"gigs": [_gig(g) for g in qs[:60]]})


def _save_gig(request, g):
    d = request.data
    title, desc = _txt(d.get("title"), 100), _txt(d.get("description"), 4000)
    price, days, rev = _int(d.get("price"), MIN_PRICE, MAX_PRICE), _int(d.get("days"), 1, 60), _int(d.get("revisions"), 0, 10)
    if len(title) < 8 or len(desc) < 30:
        return _err("Give a clear title (8+ letters) and describe what the buyer gets (30+ letters).")
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
    return Response(_gig(g, True))


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
         "test": o.provider in ("test",) or o.provider == "safepay-sandbox"}
    if full:
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


def _complete(o, why):
    with transaction.atomic():
        o = Order.objects.select_for_update().get(pk=o.pk)
        if o.status not in ("delivered", "active", "disputed"):
            return o
        o.status, o.done_at = "completed", timezone.now()
        o.save(update_fields=["status", "done_at"])
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
        o = Order.objects.create(buyer=u, seller=g.seller, gig=g, title=g.title, amount=g.price, fee=_fee(g.price), days=g.days,
                                 revisions_left=g.revisions, requirements=req)
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
    return Response({"orders": [_order(o, u) for o in qs[:100]]})


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
            o.status, o.note = "refund_due", "Cancelled by the seller"; o.save(update_fields=["status", "note"])
            _sys(o, "The seller cancelled. The buyer gets a full refund to the original payment method within 7 to 14 working days.")
            _notify(o.buyer, "Your order was cancelled by the seller; you will be refunded", "/market#order-%d" % o.id)
            try:
                from notifications.views import notify_admins
                notify_admins("market", "Refund due on marketplace order XM-%06d" % o.id, "/market#admin")
            except Exception:
                pass
        else:
            return _err("This order cannot be cancelled now. Report a problem instead.", 403)
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
    pending = Order.objects.filter(seller=u, status__in=("active", "delivered", "disputed")).aggregate(s=Sum("amount"), f=Sum("fee"))
    return Response({"balance": _balance(u), "kyc": _kyc(u), "min": MIN_PAYOUT, "methods": Payout.METHODS,
                     "in_progress": (pending["s"] or 0) - (pending["f"] or 0),
                     "earned": Entry.objects.filter(user=u, kind="earning").aggregate(s=Sum("amount"))["s"] or 0,
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
