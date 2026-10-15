"""Pay by JazzCash / Raast (/api/payproof/).
info/                 where to pay (title, Till ID, IBAN, account, QR text) - signed-in members
orders/<id>/  POST    the buyer sends the transaction ID and a screenshot for a pending Promote order
mine/                 my proofs and their status
team/ ...             the team's queue: approve (switches the order on, emails the receipt) or reject with a reason
file/<id>/            the screenshot - the buyer or the team only"""
import os
import re
import secrets

from django.utils import timezone
from django.http import HttpResponse
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PayAccount, PayProof

MAX_MB = 8
MAGIC = [(b"\xff\xd8\xff", "jpg", "image/jpeg"), (b"\x89PNG", "png", "image/png"), (b"%PDF", "pdf", "application/pdf"), (b"RIFF", "webp", "image/webp")]


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _dir():
    return os.environ.get("XC_PAYPROOF_DIR", "/var/lib/gunicorn-academy/payproofs")


def _acct():
    return PayAccount.objects.first() or PayAccount.objects.create()


def _acct_out(a):
    return {"enabled": a.enabled, "title": a.title, "bank": a.bank, "till": a.till, "iban": a.iban, "account": a.account, "qr": a.qr, "note": a.note}


def _name(u):
    return (getattr(u, "full_name", "") or getattr(u, "username", "") or u.email or "Member").strip()


def _out(p, staff=False):
    o = p.order
    d = {"id": p.id, "order": o.id, "amount": p.amount, "txn": p.txn, "sender": p.sender, "status": p.status, "reason": p.reason,
         "when": p.created_at.isoformat(), "has_file": bool(p.shot)}
    if staff:
        try:
            from shop.views import CATALOG
            c = CATALOG.get(o.product, {})
            d["item"] = "%s · %s" % (c.get("name", o.product), c.get("plans", {}).get(o.plan, (o.plan,))[0])
        except Exception:
            d["item"] = o.product
        d.update({"for": o.target_label, "user": _name(p.user), "email": p.user.email, "order_status": o.status, "order_amount": o.amount})
    return d


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def info(request):
    return Response(_acct_out(_acct()))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    rows = PayProof.objects.filter(user=request.user).select_related("order").order_by("-id")[:50]
    return Response({"proofs": [_out(p) for p in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def send(request, oid):
    from shop.models import Order
    u = request.user
    a = _acct()
    if not a.enabled:
        return _err("JazzCash payments are switched off right now.")
    o = Order.objects.filter(pk=oid, user=u).first()
    if not o:
        return _err("Order not found.", 404)
    if o.status != "pending":
        return _err("This order is not waiting for payment.")
    if PayProof.objects.filter(order=o, status=PayProof.PENDING).exists():
        return _err("You already sent the payment details for this order. The team will check them soon.")
    txn = re.sub(r"[^A-Za-z0-9\-]", "", str(request.data.get("txn") or ""))[:40]
    if len(txn) < 6:
        return _err("Write the transaction ID (TID) from your JazzCash or bank message.")
    if PayProof.objects.filter(txn__iexact=txn).exclude(status=PayProof.REJECTED).exists():
        return _err("This transaction ID was already used for another order.")
    f = request.FILES.get("file")
    name = ""
    if f:
        if f.size > MAX_MB * 1024 * 1024:
            return _err("The screenshot is over %d MB." % MAX_MB)
        raw = f.read()
        kind = next((k for k in MAGIC if raw.startswith(k[0])), None)
        if not kind:
            return _err("The screenshot must be a picture (JPG, PNG, WebP) or a PDF.")
        name = "%d_%s.%s" % (o.id, secrets.token_hex(8), kind[1])
        os.makedirs(_dir(), mode=0o700, exist_ok=True)
        with open(os.path.join(_dir(), name), "wb") as fh:
            fh.write(raw)
    else:
        return _err("Add a screenshot of the payment.")
    p = PayProof.objects.create(order=o, user=u, amount=o.amount, txn=txn, sender=re.sub(r"\s+", " ", str(request.data.get("sender") or ""))[:60].strip(), shot=name)
    o.provider = "jazzcash"; o.provider_ref = txn; o.save(update_fields=["provider", "provider_ref"])
    try:
        from notifications.views import notify_admins
        notify_admins("payment", "JazzCash payment to check: Rs %s for order %d from %s (TID %s)." % ("{:,}".format(o.amount), o.id, _name(u), txn), "/payments-admin#jazzcash")
    except Exception:
        pass
    return Response(_out(p))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def file(request, pid):
    p = PayProof.objects.filter(pk=pid).first()
    if not p or not p.shot or not (p.user_id == request.user.pk or _staff(request.user)):
        return _err("Not found.", 404)
    fp = os.path.join(_dir(), os.path.basename(p.shot))
    if not os.path.exists(fp):
        return _err("Not found.", 404)
    ext = p.shot.rsplit(".", 1)[-1]
    r = HttpResponse(open(fp, "rb").read(), content_type={"jpg": "image/jpeg", "png": "image/png", "pdf": "application/pdf", "webp": "image/webp"}.get(ext, "application/octet-stream"))
    r["Cache-Control"] = "private, no-store"
    r["X-Content-Type-Options"] = "nosniff"
    return r


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    if not _staff(request.user):
        return _err("Staff only.", 403)
    st = request.GET.get("status") or "pending"
    qs = PayProof.objects.select_related("order", "user").order_by("-id")
    if st != "all":
        qs = qs.filter(status=st)
    return Response({"account": _acct_out(_acct()), "proofs": [_out(p, True) for p in qs[:200]],
                     "waiting": PayProof.objects.filter(status=PayProof.PENDING).count()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_account(request):
    if not _staff(request.user):
        return _err("Staff only.", 403)
    a, d = _acct(), request.data
    for k, n in (("title", 80), ("bank", 60), ("till", 30), ("iban", 40), ("account", 40), ("note", 300)):
        if k in d:
            setattr(a, k, re.sub(r"\s+", " ", str(d.get(k) or "")).strip()[:n])
    if "qr" in d:
        a.qr = str(d.get("qr") or "").strip()[:600]
    if "enabled" in d:
        a.enabled = str(d.get("enabled")).lower() in ("true", "1")
    a.save()
    return Response(_acct_out(a))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_act(request, pid, act):
    if not _staff(request.user):
        return _err("Staff only.", 403)
    p = PayProof.objects.filter(pk=pid).select_related("order", "user").first()
    if not p:
        return _err("Not found.", 404)
    if p.status != PayProof.PENDING:
        return _err("Already decided.")
    o = p.order
    try:
        from notifications.views import notify
    except Exception:
        notify = None
    if act == "approve":
        if o.status != "pending":
            return _err("The order is %s, not waiting for payment." % o.status)
        from shop import views as SV
        o.provider, o.provider_ref = "jazzcash", p.txn
        o.save(update_fields=["provider", "provider_ref"])
        SV._activate(o)                     # same as a gateway payment: switches the item on and emails the receipt
        p.status = PayProof.APPROVED
        if notify:
            notify(p.user, "payment", "Payment received ✓ Your order %d is active now. Thank you!" % o.id, "/receipt?order=%d" % o.id)
    elif act == "reject":
        reason = re.sub(r"\s+", " ", str(request.data.get("reason") or "")).strip()[:200]
        if len(reason) < 4:
            return _err("Write why (the buyer sees it).")
        p.status, p.reason = PayProof.REJECTED, reason
        if notify:
            notify(p.user, "payment", "We could not confirm your payment for order %d: %s. Please check and send it again." % (o.id, reason), "/promote")
    else:
        return _err("Unknown action.")
    p.decided_by, p.decided_at = request.user, timezone.now()
    p.save(update_fields=["status", "reason", "decided_by", "decided_at"])
    return Response(_out(p, True))
