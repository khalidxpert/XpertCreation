"""/api/nearby/pass/?d=<device id> -> {"pro": true, "pass": "<signed token>", "until": "..."} or {"pro": false}.
Nearby Pro lets one phone run a group (up to 10 phones) and relay messages in Nearby chat.
Who gets it: a paid nearby_pro order that is still running, or moderators and staff (free).
The pass is signed here (ECDSA P-256) and checked on the phone with no internet. It is tied to one
device id and lasts until the order ends (at most 30 days, then the page fetches a new one when online).
The private key lives in /etc/xpertcreation/nearby-key.pem and is never sent anywhere."""
import base64
import json
import re
import time
from datetime import datetime, timedelta, timezone as dtz

from django.apps import apps
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

KEYFILE = "/etc/xpertcreation/nearby-key.pem"
MAXDAYS = 30
_key = None


def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _sign(body):
    global _key
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    if _key is None:
        with open(KEYFILE, "rb") as f:
            _key = serialization.load_pem_private_key(f.read(), password=None)
    r, s = decode_dss_signature(_key.sign(body, ec.ECDSA(hashes.SHA256())))
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _until(u):
    """When Nearby Pro ends for this user, or None."""
    now = timezone.now()
    if getattr(u, "is_moderator", False) or u.is_staff or u.is_superuser:
        return now + timedelta(days=MAXDAYS)
    Order = apps.get_model("shop", "Order")
    o = Order.objects.filter(user=u, product="nearby_pro", status="paid", ends_at__gt=now).order_by("-ends_at").first()
    return o.ends_at if o else None


@api_view(["GET"])
@permission_classes([AllowAny])
def nearby_pass(request):
    u = request.user
    if not u.is_authenticated:
        return Response({"pro": False, "login": True})
    dev = str(request.GET.get("d", ""))[:40]
    if not re.fullmatch(r"[0-9a-f]{8,40}", dev):
        return Response({"detail": "Missing device id."}, status=400)
    end = _until(u)
    if not end:
        return Response({"pro": False})
    exp = int(min(end.timestamp(), time.time() + MAXDAYS * 86400))
    free = bool(getattr(u, "is_moderator", False) or u.is_staff or u.is_superuser)
    body = json.dumps({"u": u.pk, "n": (u.get_full_name() or u.username)[:40], "d": dev, "exp": exp, "p": "pro"},
                      separators=(",", ":")).encode()
    try:
        sig = _sign(body)
    except Exception:
        return Response({"detail": "Nearby Pro is not set up on the server yet."}, status=503)
    return Response({"pro": True, "free": free, "pass": _b64u(body) + "." + _b64u(sig),
                     "until": datetime.fromtimestamp(exp, tz=dtz.utc).isoformat()})


# ---- one-scan pairing: the second phone's reply is passed back through here when it has internet.
# Kept 3 minutes in the cache, read once. Only pairing codes (no messages) ever pass through.
import json as _json
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

_ROOM = re.compile(r"[0-9a-f]{16,48}")


@csrf_exempt
def sig(request, room):
    if not _ROOM.fullmatch(room or ""):
        return JsonResponse({"detail": "Bad room."}, status=400)
    k = "xcn:sig:" + room
    if request.method == "POST":
        try:
            code = str(_json.loads(request.body or b"{}").get("code", ""))
        except Exception:
            code = ""
        if not code.startswith(("XCN0.", "XCN1.")) or len(code) > 6000:
            return JsonResponse({"detail": "Not a Nearby code."}, status=400)
        if cache.get(k + ":n", 0) >= 5:
            return JsonResponse({"detail": "Too many tries."}, status=429)
        cache.set(k + ":n", cache.get(k + ":n", 0) + 1, 180)
        cache.set(k, code, 180)
        return JsonResponse({"ok": True})
    code = cache.get(k)
    if code:
        cache.delete(k)
    r = JsonResponse({"code": code})
    r["Cache-Control"] = "no-store"
    return r
