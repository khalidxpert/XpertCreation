"""Google Play Billing for the XpertCreation Android app (TWA + Digital Goods API).

The app asks Google for the price and the purchase; this server checks every purchase
with Google before switching anything on, then consumes it so it can be bought again.
Switched on only when the service-account key exists at KEY_FILE.
"""
import json
import logging
import os
import threading
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from shop.models import Order
from .models import PlayPurchase

log = logging.getLogger(__name__)
PACKAGE = "com.xpertcreation.app"
KEY_FILE = os.environ.get("PLAY_KEY_FILE", "/etc/xpertcreation/play-key.json")
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/%s/purchases/products/%s/tokens/%s"
_lock = threading.Lock()
_creds = {"c": None}


class PlayThrottle(UserRateThrottle):
    rate = "30/min"


def _sv():
    import shop.views as SV          # late import: shop.views is patched at the end of the module
    return SV


def ready():
    return os.path.isfile(KEY_FILE) and os.access(KEY_FILE, os.R_OK)


def sku_of(product, plan):
    return ("%s_%s" % (product, plan)).lower()


def _session():
    """An authorised HTTP session for the Play Developer API (token refreshed when needed)."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    with _lock:
        if _creds["c"] is None:
            _creds["c"] = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=[SCOPE])
        return AuthorizedSession(_creds["c"])


def google_get(sku, token):
    r = _session().get(API % (PACKAGE, sku, token), timeout=20)
    if r.status_code != 200:
        return None, "Google said %s" % r.status_code
    return r.json(), ""


def google_consume(sku, token):
    r = _session().post((API % (PACKAGE, sku, token)) + ":consume", timeout=20)
    return r.status_code in (200, 204)


@api_view(["GET"])
@permission_classes([AllowAny])
def config(request):
    SV = _sv()
    skus = {}
    for k, c in SV.CATALOG.items():
        for p in c["plans"]:
            skus.setdefault(k, {})[p] = sku_of(k, p)
    return Response({"enabled": ready(), "package": PACKAGE, "skus": skus})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PlayThrottle])
def order(request):
    """Create a pending order to be paid through Google Play (no Safepay/JazzCash step)."""
    if not ready():
        return Response({"detail": "Google Play payments are not switched on yet."}, status=403)
    SV = _sv(); u = request.user; d = request.data
    p, plan = d.get("product"), d.get("plan")
    if p not in SV.CATALOG or plan not in SV.CATALOG[p]["plans"]:
        return Response({"detail": "Choose an item and a plan."}, status=400)
    if p == "blue_tick" and Order.objects.filter(user=u, product="blue_tick", status="paid").exists():
        return Response({"detail": "You have already paid for the blue tick check."}, status=400)
    tid, label = SV._target(u, SV.CATALOG[p]["target"], d.get("target"))
    if tid is None:
        return Response({"detail": label}, status=400)
    o = Order.objects.create(user=u, product=p, plan=plan, target_id=tid, target_label=label[:160],
                             amount=SV.price(p, plan), provider="googleplay")
    return Response({"order": o.id, "sku": sku_of(p, plan)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PlayThrottle])
def verify(request):
    """body: {token, sku, order?}. Checks the purchase with Google, switches the item on, consumes it."""
    if not ready():
        return Response({"detail": "Google Play payments are not switched on yet."}, status=403)
    u = request.user
    token = str(request.data.get("token") or "").strip()
    sku = str(request.data.get("sku") or "").strip().lower()
    oid = request.data.get("order")
    if not token or not sku or len(token) > 600:
        return Response({"detail": "Missing purchase."}, status=400)

    pp = PlayPurchase.objects.filter(token=token).first()
    if pp and pp.user_id != u.id:
        return Response({"detail": "This purchase belongs to another account."}, status=403)
    if pp and pp.state in ("paid", "consumed"):
        if pp.state == "paid" and google_consume(pp.sku, token):
            pp.state = "consumed"; pp.save(update_fields=["state", "updated_at"])
        return Response({"ok": True, "order": pp.order_id, "already": True})

    data, err = google_get(sku, token)
    if data is None:
        return Response({"detail": "Google could not confirm this purchase (%s)." % err}, status=400)
    if int(data.get("purchaseState", 1)) != 0:            # 0 = purchased, 1 = cancelled, 2 = pending
        msg = "The payment is still pending with Google." if int(data.get("purchaseState", 1)) == 2 else "This purchase was cancelled."
        return Response({"detail": msg}, status=409)

    with transaction.atomic():
        pp, _ = PlayPurchase.objects.select_for_update().get_or_create(token=token, defaults={"sku": sku, "user": u})
        if pp.state in ("paid", "consumed"):
            return Response({"ok": True, "order": pp.order_id, "already": True})
        since = timezone.now() - timedelta(days=3)
        qs = Order.objects.select_for_update().filter(user=u, status__in=["pending", "cancelled"], provider="googleplay", created_at__gte=since)
        o = qs.filter(pk=oid).first() if oid else None
        if o is None:                                       # app closed mid-purchase: match the newest waiting order for this item
            for cand in sorted(qs.order_by("-created_at")[:20], key=lambda x: x.status != "pending"):
                if sku_of(cand.product, cand.plan) == sku:
                    o = cand; break
        if o is None or sku_of(o.product, o.plan) != sku:
            pp.state, pp.note = "bad", "no matching order"; pp.save()
            log.warning("playbill: purchase %s for %s has no matching order", data.get("orderId"), sku)
            return Response({"detail": "We could not match this payment to an order. Contact support with Google order %s." % data.get("orderId", "")}, status=409)
        o.provider_ref = (data.get("orderId") or "")[:120]
        o.provider = "googleplay-test" if str(data.get("purchaseType", "")) == "0" else "googleplay"   # setup_orders_v1: 0 = licence test
        o.save(update_fields=["provider_ref", "provider"])
        _sv()._activate(o)
        pp.order, pp.gp_order, pp.state, pp.sku = o, (data.get("orderId") or "")[:80], "paid", sku
        pp.save()
    if google_consume(sku, token):
        pp.state = "consumed"; pp.save(update_fields=["state", "updated_at"])
    return Response({"ok": True, "order": o.id})
