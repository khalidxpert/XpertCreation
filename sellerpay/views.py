"""Pay the seller directly (/api/sellerpay/).
avail/?kind=store&ids=1,2 | ?kind=food&slug=x   which shops / restaurants take JazzCash / bank payments
me/                    seller: GET / POST my payment details (JazzCash, EasyPaisa, bank IBAN, Raast ID, note, on/off)
me/qr/                 seller: POST a QR picture (file) / DELETE it
order/<kind>/<id>/     buyer: GET where to pay + my uploads, POST a screenshot (file, txn, sender)
                       seller: GET the uploads for this order
proof/<id>/ok|bad/     seller: payment received / not received (with a reason)
file/<id>/             the screenshot (buyer, seller, team only)
qr/<user id>/          a seller's QR picture (signed-in members)"""
import os
import re
import secrets

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Proof, SellerPay

PRIV = os.path.join(str(settings.BASE_DIR), "private", "sellerpay")


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _num(v):
    p = re.sub(r"[^\d+]", "", str(v or ""))[:20]
    return p if len(re.sub(r"\D", "", p)) >= 10 else ""


def _notify(user, text, link):
    try:
        from notifications.views import notify
        notify(user, "payment", text, link)
    except Exception:
        pass


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def ready(sp):
    return bool(sp and sp.on and (sp.jazzcash or sp.easypaisa or sp.iban or sp.raast or sp.qr))


def direct_ok(user_id):
    return ready(SellerPay.objects.filter(user_id=user_id).first())


def _save(f, prefix):
    if not f:
        return None, "Choose a picture."
    if f.size > 8 * 1024 * 1024:
        return None, "The picture is over 8 MB."
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); im.load()
    except Exception:
        return None, "That file is not a picture we can read."
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1600, 1600), Image.LANCZOS)
    os.makedirs(PRIV, exist_ok=True)
    name = "%s_%s.jpg" % (prefix, secrets.token_hex(10))
    im.save(os.path.join(PRIV, name), "JPEG", quality=85)
    return name, None


def _rm(name):
    if name:
        try:
            os.remove(os.path.join(PRIV, os.path.basename(name)))
        except OSError:
            pass


def _order(kind, oid):
    """(buyer_id, seller_user_id, amount, number, buyer link, seller link) for a direct-payment order, or None."""
    try:
        if kind == "store":
            from store.models import Order
            o = Order.objects.select_related("merchant").filter(pk=oid, payment="direct").first()
            return o and (o.buyer_id, o.merchant.user_id, o.total, "XS-%06d" % o.id, "/store#order-%d" % o.id, "/store#sorder-%d" % o.id, o.status)
        if kind == "food":
            from xfood.models import FoodOrder
            o = FoodOrder.objects.select_related("restaurant").filter(pk=oid, payment="direct").first()
            return o and (o.buyer_id, o.restaurant.user_id, o.total, "F-%05d" % o.id, "/food#o-%d" % o.id, "/food#partner", o.status)
    except Exception:
        return None
    return None


def _info(sp):
    return {"jazzcash": sp.jazzcash, "jazzcash_name": sp.jazzcash_name, "easypaisa": sp.easypaisa, "easypaisa_name": sp.easypaisa_name,
            "bank": sp.bank, "title": sp.title, "iban": sp.iban, "raast": sp.raast, "note": sp.note,
            "qr": ("/api/sellerpay/qr/%d/?v=%s" % (sp.user_id, sp.qr[-12:-4])) if sp.qr else ""}


def _p(p):
    return {"id": p.id, "amount": p.amount, "txn": p.txn, "sender": p.sender, "status": p.status, "reason": p.reason, "when": p.created_at.isoformat(),
            "shot": "/api/sellerpay/file/%d/" % p.id if p.shot else ""}


@api_view(["GET"])
@permission_classes([AllowAny])
def avail(request):
    g = request.GET
    try:
        if g.get("kind") == "store":
            from store.models import Merchant
            ids = [int(x) for x in str(g.get("ids") or "").split(",") if x.strip().isdigit()][:40]
            return Response({str(m.id): direct_ok(m.user_id) for m in Merchant.objects.filter(pk__in=ids)})
        if g.get("kind") == "food":
            from xfood.models import Restaurant
            r = Restaurant.objects.filter(slug=str(g.get("slug") or "")[:90]).first()
            return Response({r.slug: direct_ok(r.user_id)} if r else {})
    except Exception:
        pass
    return Response({})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def me(request):
    sp, _ = SellerPay.objects.get_or_create(user=request.user)
    if request.method == "POST":
        d = request.data
        sp.jazzcash, sp.easypaisa = _num(d.get("jazzcash")), _num(d.get("easypaisa"))
        sp.jazzcash_name, sp.easypaisa_name = _txt(d.get("jazzcash_name"), 60), _txt(d.get("easypaisa_name"), 60)
        sp.bank, sp.title = _txt(d.get("bank"), 60), _txt(d.get("title"), 80)
        iban = re.sub(r"\s", "", str(d.get("iban") or "")).upper()[:34]
        if iban and not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", iban):
            return _err("That IBAN does not look right. A Pakistani IBAN starts with PK and has 24 letters and numbers.")
        sp.iban, sp.raast, sp.note = iban, _txt(d.get("raast"), 40), _txt(d.get("note"), 200)
        sp.on = bool(d.get("on"))
        if sp.on and not (sp.jazzcash or sp.easypaisa or sp.iban or sp.raast or sp.qr):
            return _err("Add at least one way to pay you (JazzCash, EasyPaisa, bank IBAN, Raast ID or a QR picture) before you switch it on.")
        sp.save()
    out = _info(sp)
    out.update({"on": sp.on, "ready": ready(sp)})
    return Response(out)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def me_qr(request):
    sp, _ = SellerPay.objects.get_or_create(user=request.user)
    if request.method == "DELETE":
        _rm(sp.qr); sp.qr = ""; sp.save(update_fields=["qr"])
        return Response({"ok": True})
    name, e = _save(request.FILES.get("file"), "qr%d" % request.user.pk)
    if e:
        return _err(e)
    _rm(sp.qr); sp.qr = name; sp.save(update_fields=["qr"])
    return Response(_info(sp))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def order(request, kind, oid):
    u = request.user
    o = _order(kind, oid)
    if not o or u.pk not in (o[0], o[1]) and not _staff(u):
        return _err("Order not found.", 404)
    buyer_id, seller_id, amount, no, blink, slink, status = o
    proofs = Proof.objects.filter(kind=kind, order_id=oid)
    if request.method == "GET":
        sp = SellerPay.objects.filter(user_id=seller_id).first()
        out = {"role": "buyer" if u.pk == buyer_id else "seller", "amount": amount, "no": no, "status": status,
               "paid": proofs.filter(status="ok").exists(), "proofs": [_p(p) for p in proofs[:20]]}
        if u.pk == buyer_id:
            out["pay"] = _info(sp) if ready(sp) else None
        return Response(out)
    if u.pk != buyer_id:
        return _err("Only the buyer can send the payment.", 403)
    if status in ("cancelled", "rejected", "refunded"):
        return _err("This order is cancelled.")
    if proofs.filter(status="ok").exists():
        return _err("The seller already confirmed your payment.")
    if proofs.filter(status="pending").count() >= 2:
        return _err("You already sent a screenshot. Wait for the seller to check it.")
    txn = _txt(request.data.get("txn"), 40)
    if len(txn) < 4:
        return _err("Give the transaction ID (TID) from your payment message.")
    name, e = _save(request.FILES.get("file"), "pay%d" % u.pk)
    if e:
        return _err("Add the screenshot of your payment. " + e)
    p = Proof.objects.create(kind=kind, order_id=oid, buyer=u, seller_id=seller_id, amount=amount, txn=txn, sender=_txt(request.data.get("sender"), 60), shot=name)
    from django.contrib.auth import get_user_model
    s = get_user_model().objects.filter(pk=seller_id).first()
    if s:
        _notify(s, "\U0001F4B3 Payment screenshot for order %s: Rs %s (TID %s). Check your account and confirm." % (no, "{:,}".format(amount), txn), slink)
    return Response(_p(p), status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def proof_act(request, pk, act):
    p = Proof.objects.select_related("buyer").filter(pk=pk, seller=request.user).first()
    if not p:
        return _err("Not found.", 404)
    o = _order(p.kind, p.order_id)
    if act == "ok":
        p.status, p.reason = "ok", ""
        _notify(p.buyer, "✅ The seller confirmed your payment of Rs %s for order %s." % ("{:,}".format(p.amount), o[3] if o else ""), o[4] if o else "/")
    elif act == "bad":
        p.status, p.reason = "bad", _txt(request.data.get("reason"), 200) or "The money did not reach our account."
        _notify(p.buyer, "Payment for order %s was not found: %s Please check and send again." % (o[3] if o else "", p.reason), o[4] if o else "/")
    else:
        return _err("Unknown action.")
    p.decided_at = timezone.now()
    p.save(update_fields=["status", "reason", "decided_at"])
    return Response(_p(p))


def _serve(name):
    f = os.path.join(PRIV, os.path.basename(name or ""))
    if not name or not os.path.isfile(f):
        raise Http404
    r = FileResponse(open(f, "rb"), content_type="image/jpeg")
    r["Cache-Control"] = "private, max-age=3600"
    return r


def file(request, pk):
    u = request.user
    p = Proof.objects.filter(pk=pk).first()
    if not p or not u.is_authenticated or (u.pk not in (p.buyer_id, p.seller_id) and not _staff(u)):
        raise Http404
    return _serve(p.shot)


def qr(request, uid):
    if not request.user.is_authenticated:
        raise Http404
    sp = SellerPay.objects.filter(user_id=uid, on=True).first()
    return _serve(sp.qr if sp else "")
