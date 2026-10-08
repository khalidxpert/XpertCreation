"""Pay per order: profile boost, post boost, featured job, Company Pro, blue tick fee.
Mode: off (nothing for sale), test (staff only, 'simulate payment'), live (members, real gateway - added later)."""
import hashlib
import hmac
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import timedelta

from django.apps import apps
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import Order, ShopSetting


# ---- Safepay (standard checkout: init with the public key, return checked with the secret key)
def _sp():
    """Safepay settings from the API's .env (keys are never sent to the browser)."""
    env = {}
    try:
        from django.conf import settings
        path = os.path.join(settings.BASE_DIR, ".env")
        env = dict(re.findall(r"^(SAFEPAY_[A-Z_]+)=(.*)$", open(path).read(), re.M))
    except Exception:
        pass
    e = (env.get("SAFEPAY_ENV") or "").strip()
    return {"env": e, "pub": (env.get("SAFEPAY_PUBLIC_KEY") or "").strip(), "sec": (env.get("SAFEPAY_SECRET_KEY") or "").strip(),
            "api": "https://sandbox.api.getsafepay.com" if e == "sandbox" else "https://api.getsafepay.com",
            "checkout": ("https://sandbox.api.getsafepay.com" if e == "sandbox" else "https://api.getsafepay.com") + "/checkout/pay"}


def sp_ready():
    c = _sp(); return bool(c["env"] in ("sandbox", "production") and c["pub"] and c["sec"])


def _sp_init(amount):
    c = _sp()
    body = json.dumps({"client": c["pub"], "amount": amount, "currency": "PKR", "environment": c["env"]}).encode()
    req = urllib.request.Request(c["api"] + "/order/v1/init", data=body, headers={"Content-Type": "application/json", "Accept": "application/json",
                                 "User-Agent": "Mozilla/5.0 (compatible; XpertCreation/1.0; +https://xpertcreation.com)"})
    d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    return d["data"]["token"]


def _sp_pass():
    """A short-lived checkout pass from Safepay (asked for with the secret key, which never leaves the server)."""
    c = _sp()
    req = urllib.request.Request(c["api"] + "/client/passport/v1/token", data=b"{}", headers={"Content-Type": "application/json", "Accept": "application/json",
                                 "X-SFPY-MERCHANT-SECRET": c["sec"], "User-Agent": "Mozilla/5.0 (compatible; XpertCreation/1.0; +https://xpertcreation.com)"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())["data"]


def _sp_checkout_url(order, token):
    c = _sp(); site = "https://xpertcreation.com"
    q = {"env": c["env"], "beacon": token, "source": "custom", "order_id": str(order.id), "tbt": _sp_pass(),
         "redirect_url": site + "/api/shop/safepay/return/", "cancel_url": site + "/promote?cancel=1"}
    return c["checkout"] + "?" + urllib.parse.urlencode(q)


def sp_sig_ok(tracker, sig):
    sec = _sp()["sec"]
    if not (sec and tracker and sig):
        return False
    good = hmac.new(sec.encode(), tracker.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, str(sig))

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
    if sp_ready():
        try:
            tok = _sp_init(o.amount)
        except Exception:
            o.status = "cancelled"; o.note = "could not start payment"; o.save(update_fields=["status", "note"])
            return Response({"detail": "Could not start the payment. Please try again in a minute."}, status=502)
        o.provider, o.provider_ref = "safepay-" + _sp()["env"], tok; o.save(update_fields=["provider", "provider_ref"])
        return Response({"order": _out(o), "next": "gateway", "checkout": _sp_checkout_url(o, tok)}, status=201)
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
            if request.data["mode"] == "live" and not (sp_ready() and _sp()["env"] == "production"):
                return Response({"detail": "Live needs Safepay production keys first (sandbox keys are for TEST mode)."}, status=400)
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
    return Response({"mode": s.mode, "gateway": ("Safepay " + _sp()["env"]) if sp_ready() else "none", "catalog": _catalog(s), "orders": [dict(_out(o), user=(getattr(o.user, "full_name", "") or o.user.username)) for o in rows],
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



# ---- Safepay sends the member back here after paying (GET or POST); the signature decides.
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def safepay_return(request):
    d = request.POST if request.method == "POST" else request.GET
    tracker, sig, oid = d.get("tracker") or d.get("beacon") or "", d.get("sig") or d.get("signature") or "", d.get("order_id") or ""
    o = Order.objects.filter(pk=int(oid) if str(oid).isdigit() else 0, provider_ref=tracker).first()
    if not o or not sp_sig_ok(tracker, sig):
        return HttpResponseRedirect("/promote?failed=1")
    if o.status == "pending":
        ref = d.get("reference") or ""
        if ref:
            o.note = ("safepay ref " + ref)[:300]
        _activate(o)
    return HttpResponseRedirect("/promote?paid=%d" % o.id)


# ---- Safepay Payments 2.0 / Express Checkout (installed by patch_safepay_v3). Replaces the old init flow.
# Steps: tracker (/order/payments/v3/) -> passport token (tbt) -> hosted checkout (/embedded/) -> verify with reporter.
import json as _j3
import os
import re
import time as _t3
import urllib.error as _ue3
import urllib.parse as _up3
import urllib.request as _ur3
from django.http import HttpResponseRedirect as _Redirect3, JsonResponse as _Json3
from django.views.decorators.csrf import csrf_exempt as _csrf_exempt3
from rest_framework.decorators import api_view as _api_view3, permission_classes as _perm3
from rest_framework.permissions import AllowAny as _AllowAny3, IsAuthenticated as _IsAuth3
from rest_framework.response import Response as _Resp3

_SITE3 = "https://xpertcreation.com"


def _sp3():
    """Keys from the API's .env (never sent to the browser)."""
    env = {}
    try:
        from django.conf import settings
        env = dict(re.findall(r"^(SAFEPAY_[A-Z_]+)=(.*)$", open(os.path.join(settings.BASE_DIR, ".env")).read(), re.M))
    except Exception:
        pass
    e = (env.get("SAFEPAY_ENV") or "").strip().strip('"\'')
    sb = e == "sandbox"
    return {"env": e, "pub": (env.get("SAFEPAY_PUBLIC_KEY") or "").strip().strip('"\''),
            "sec": (env.get("SAFEPAY_SECRET_KEY") or "").strip().strip('"\''),
            "api": "https://sandbox.api.getsafepay.com" if sb else "https://api.getsafepay.com",
            "checkout": "https://sandbox.api.getsafepay.com/embedded/" if sb else "https://getsafepay.com/embedded/"}


def sp_ready():
    c = _sp3(); return bool(c["env"] in ("sandbox", "production") and c["pub"] and c["sec"])


def _sp3_call(method, path, body=None):
    c = _sp3()
    req = _ur3.Request(c["api"] + path, method=method, data=_j3.dumps(body).encode() if body is not None else None,
                       headers={"Content-Type": "application/json", "Accept": "application/json", "X-SFPY-MERCHANT-SECRET": c["sec"],
                                "User-Agent": "Mozilla/5.0 (compatible; XpertCreation/1.0; +https://xpertcreation.com)"})
    try:
        return _j3.loads(_ur3.urlopen(req, timeout=20).read().decode() or "{}")
    except _ue3.HTTPError as ex:
        raise RuntimeError("Safepay %s %s -> HTTP %s %s" % (method, path, ex.code, ex.read().decode(errors="replace")[:300]))


def sp3_start(o):
    """Create the payment session and return (tracker, checkout_url)."""
    c = _sp3()
    d = _sp3_call("POST", "/order/payments/v3/", {"merchant_api_key": c["pub"], "intent": "CYBERSOURCE", "mode": "payment", "entry_mode": "raw",
                                                  "currency": "PKR", "amount": int(o.amount) * 100,
                                                  "metadata": {"order_id": str(o.id), "source": "xpertcreation"}, "include_fees": False})
    tracker = d["data"]["tracker"]["token"]
    tbt = _sp3_call("POST", "/client/passport/v1/token")["data"]
    q = {"environment": c["env"], "tracker": tracker, "tbt": tbt, "source": "hosted",
         "redirect_url": _SITE3 + "/api/shop/safepay/return/", "cancel_url": _SITE3 + "/promote?cancel=1"}
    return tracker, c["checkout"] + "?" + _up3.urlencode(q)


def sp3_info(tracker):
    """Reporter answer for this tracker. Safepay puts the state at data.state (older docs said data.tracker.state)."""
    try:
        d = (_sp3_call("GET", "/reporter/api/v1/payments/" + _up3.quote(tracker, safe="")).get("data") or {})
    except Exception:
        return "", None
    st = d.get("state") or (d.get("tracker") or {}).get("state") or ""
    tot = d.get("purchase_totals") or (d.get("tracker") or {}).get("purchase_totals") or {}
    amt = (tot.get("quote_amount") or {}).get("amount")
    return st, amt


def sp3_state(tracker):
    return sp3_info(tracker)[0]


def sp3_settle(o, wait=0):
    """Mark the order paid only if Safepay says the tracker ended AND the amount matches. Returns True when paid."""
    if o.status == "paid":
        return True
    if o.status != "pending" or not o.provider_ref:
        return False
    for i in range(wait + 1):
        st, amt = sp3_info(o.provider_ref)
        if st == "TRACKER_ENDED":
            if amt is not None and int(amt) != int(o.amount) * 100:
                o.note = ("amount mismatch: safepay %s, order %s" % (amt, o.amount * 100))[:300]; o.save(update_fields=["note"])
                return False
            _activate(o); return True
        if i < wait:
            _t3.sleep(2)
    return False


@_api_view3(["POST"])
@_perm3([_IsAuth3])
def order(request):
    s = setting(); u = request.user; d = request.data
    if not (s.mode == "live" or (s.mode == "test" and _staff(u))):
        return _Resp3({"detail": "Paid items are not available yet."}, status=403)
    p, plan = d.get("product"), d.get("plan")
    if p not in CATALOG or plan not in CATALOG[p]["plans"]:
        return _Resp3({"detail": "Choose an item and a plan."}, status=400)
    if p == "blue_tick" and Order.objects.filter(user=u, product="blue_tick", status="paid").exists():
        return _Resp3({"detail": "You have already paid for the blue tick check."}, status=400)
    tid, label = _target(u, CATALOG[p]["target"], d.get("target"))
    if tid is None:
        return _Resp3({"detail": label}, status=400)
    o = Order.objects.create(user=u, product=p, plan=plan, target_id=tid, target_label=label[:160], amount=price(p, plan, s),
                             provider="test" if s.mode == "test" else "")
    if sp_ready():
        try:
            tracker, url = sp3_start(o)
        except Exception as ex:
            o.status = "cancelled"; o.note = ("could not start payment: %s" % ex)[:300]; o.save(update_fields=["status", "note"])
            return _Resp3({"detail": "Could not start the payment. Please try again in a minute."}, status=502)
        o.provider, o.provider_ref = "safepay-" + _sp3()["env"], tracker
        o.save(update_fields=["provider", "provider_ref"])
        return _Resp3({"order": _out(o), "next": "gateway", "checkout": url}, status=201)
    return _Resp3({"order": _out(o), "next": "simulate" if s.mode == "test" else "gateway"}, status=201)


@_csrf_exempt3
def safepay_return(request):
    """Safepay sends the member back with ?tracker=track_... ; we ask Safepay directly whether it was paid."""
    d = request.POST if request.method == "POST" else request.GET
    tracker = (d.get("tracker") or "").strip()
    o = Order.objects.filter(provider_ref=tracker).first() if tracker.startswith("track_") else None
    if not o:
        return _Redirect3("/promote?failed=1")
    if sp3_settle(o, wait=3):
        return _Redirect3("/promote?paid=%d" % o.id)
    return _Redirect3("/promote?failed=1&order=%d" % o.id)


def _sp3_trackers(x, out):
    if isinstance(x, dict):
        for v in x.values(): _sp3_trackers(v, out)
    elif isinstance(x, list):
        for v in x: _sp3_trackers(v, out)
    elif isinstance(x, str) and x.startswith("track_") and len(x) < 80:
        out.add(x)
    return out


@_csrf_exempt3
def safepay_webhook(request):
    """Webhook is only a hint: every tracker in it is re-checked with Safepay before anything is activated."""
    try:
        body = _j3.loads(request.body.decode() or "{}")
    except Exception:
        body = {}
    done = []
    for tr in list(_sp3_trackers(body, set()))[:5]:
        o = Order.objects.filter(provider_ref=tr).first()
        if o and sp3_settle(o):
            done.append(o.id)
    return _Json3({"ok": True, "paid": done})


_shop_v2 = shop


@_api_view3(["GET"])
@_perm3([_AllowAny3])
def shop(request):
    """Before listing, re-check this member's recent unpaid Safepay orders (covers a missed return or webhook)."""
    u = request.user
    if u.is_authenticated:
        from datetime import timedelta as _td3
        from django.utils import timezone as _tz3
        for o in Order.objects.filter(user=u, status="pending", provider__startswith="safepay-",
                                      created_at__gte=_tz3.now() - _td3(hours=2)).order_by("-id")[:3]:
            sp3_settle(o)
    return _shop_v2(request._request)
