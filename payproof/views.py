"""Pay by JazzCash / Raast (/api/payproof/) - for Promote, Freelance and Store orders.
info/                    where to pay (title, Till ID, IBAN, account, QR text) - signed-in members
orders/<id>/     POST    Promote order: the buyer sends the transaction ID and a screenshot
pay/<kind>/<ref>/ GET    what to pay for a Freelance order (ref = order id) or a Store cart (ref = group) + any proof already sent
pay/<kind>/<ref>/ POST   send the transaction ID and screenshot for it
mine/                    my proofs and their status
team/ ...                the team's queue: approve (switches the order on, like a gateway payment) or reject with a reason
file/<id>/               the screenshot - the buyer or the team only"""
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


# ---------------------------------------------------------------- what is being paid for
class Target:
    """The order(s) a proof pays for. rows: the order objects; label: what the team sees; link: where the buyer goes."""

    def __init__(self, kind, ref, rows, amount, label, item, link, buyer_id):
        self.kind, self.ref, self.rows, self.amount, self.label, self.item, self.link, self.buyer_id = kind, ref, rows, amount, label, item, link, buyer_id

    @property
    def pending(self):
        return bool(self.rows) and all(r.status == "pending" for r in self.rows)


def _target(kind, ref, user=None):
    ref = str(ref or "")[:40]
    if kind == "promote":
        from shop.models import Order
        o = Order.objects.filter(pk=int(ref) if ref.isdigit() else 0).first()
        if not o or (user and o.user_id != user.pk):
            return None
        try:
            from shop.views import CATALOG
            c = CATALOG.get(o.product, {}); item = "%s · %s" % (c.get("name", o.product), c.get("plans", {}).get(o.plan, (o.plan,))[0])
        except Exception:
            item = o.product
        if o.target_label:
            item += " · for " + o.target_label
        return Target(kind, ref, [o], o.amount, "Promote order %d" % o.id, item, "/promote", o.user_id)
    if kind == "freelance":
        from market.models import Order
        o = Order.objects.filter(pk=int(ref) if ref.isdigit() else 0).select_related("seller").first()
        if not o or (user and o.buyer_id != user.pk):
            return None
        return Target(kind, ref, [o], o.amount, "Freelance XM-%06d" % o.id, "%s · seller %s" % (o.title, _name(o.seller)), "/market#order-%d" % o.id, o.buyer_id)
    if kind == "store":
        from store.models import Order
        qs = Order.objects.filter(group=ref, payment="online").select_related("merchant") if re.match(r"^[0-9a-f]{6,20}$", ref) else Order.objects.none()
        if user:
            qs = qs.filter(buyer=user)
        rows = [o for o in qs if o.status in ("pending", "placed", "confirmed", "shipped", "delivered", "completed", "cancelled")]
        if not rows:
            return None
        live = [o for o in rows if o.status != "cancelled"] or rows
        return Target(kind, ref, live, sum(o.total for o in live), "Store " + ", ".join("XS-%06d" % o.id for o in live),
                      " + ".join("%s (%d item%s)" % (o.merchant.name, len(o.items or []), "" if len(o.items or []) == 1 else "s") for o in live),
                      "/store#orders", live[0].buyer_id)
    return None


def _target_of(p):
    if p.kind == "promote" and not p.ref and p.order_id:
        return _target("promote", str(p.order_id))
    return _target(p.kind, p.ref)


def _out(p, staff=False):
    d = {"id": p.id, "kind": p.kind, "ref": p.ref or str(p.order_id or ""), "order": p.order_id if p.kind == "promote" else p.ref,
         "amount": p.amount, "txn": p.txn, "sender": p.sender, "status": p.status, "reason": p.reason,
         "when": p.created_at.isoformat(), "has_file": bool(p.shot)}
    if staff:
        t = _target_of(p)
        d.update({"order": t.label if t else p.ref, "item": t.item if t else "(order removed)", "for": "",
                  "user": _name(p.user), "email": p.user.email,
                  "order_status": ", ".join(sorted(set(r.status for r in t.rows))) if t else "removed", "order_amount": t.amount if t else 0})
    return d


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def info(request):
    return Response(_acct_out(_acct()))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    rows = PayProof.objects.filter(user=request.user).order_by("-id")[:50]
    return Response({"proofs": [_out(p) for p in rows]})


def _save_shot(f, prefix):
    if not f:
        return None, "Add a screenshot of the payment."
    if f.size > MAX_MB * 1024 * 1024:
        return None, "The screenshot is over %d MB." % MAX_MB
    raw = f.read()
    kind = next((k for k in MAGIC if raw.startswith(k[0])), None)
    if not kind:
        return None, "The screenshot must be a picture (JPG, PNG, WebP) or a PDF."
    name = "%s_%s.%s" % (prefix, secrets.token_hex(8), kind[1])
    os.makedirs(_dir(), mode=0o700, exist_ok=True)
    with open(os.path.join(_dir(), name), "wb") as fh:
        fh.write(raw)
    return name, None


def _create(request, t):
    """Shared by Promote, Freelance and Store: checks, saves the screenshot, records the proof, tells the team."""
    u = request.user
    if not _acct().enabled:
        return _err("JazzCash payments are switched off right now.")
    if not t.pending:
        return _err("This order is not waiting for payment.")
    if PayProof.objects.filter(kind=t.kind, ref=t.ref, status=PayProof.PENDING).exists():
        return _err("You already sent the payment details for this order. The team will check them soon.")
    txn = re.sub(r"[^A-Za-z0-9\-]", "", str(request.data.get("txn") or ""))[:40]
    if len(txn) < 6:
        return _err("Write the transaction ID (TID) from your JazzCash or bank message.")
    if PayProof.objects.filter(txn__iexact=txn).exclude(status=PayProof.REJECTED).exists():
        return _err("This transaction ID was already used for another order.")
    name, e = _save_shot(request.FILES.get("file"), "%s%s" % (t.kind[0], re.sub(r"[^0-9a-z]", "", t.ref)[:20]))
    if e:
        return _err(e)
    p = PayProof.objects.create(kind=t.kind, ref=t.ref, order=t.rows[0] if t.kind == "promote" else None, user=u, amount=t.amount, txn=txn,
                                sender=re.sub(r"\s+", " ", str(request.data.get("sender") or ""))[:60].strip(), shot=name)
    for r in t.rows:
        type(r).objects.filter(pk=r.pk).update(provider="jazzcash", provider_ref=txn)
    try:
        from notifications.views import notify_admins
        notify_admins("payment", "JazzCash payment to check: Rs %s for %s from %s (TID %s)." % ("{:,}".format(t.amount), t.label, _name(u), txn), "/payments-admin#jazzcash")
    except Exception:
        pass
    return Response(_out(p))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def send(request, oid):
    t = _target("promote", str(oid), request.user)
    if not t:
        return _err("Order not found.", 404)
    return _create(request, t)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def send_any(request, kind, ref):
    if kind not in ("promote", "freelance", "store"):
        return _err("Unknown.", 404)
    t = _target(kind, ref, request.user)
    if not t:
        return _err("Order not found.", 404)
    if request.method == "GET":
        last = PayProof.objects.filter(kind=kind, ref=t.ref).order_by("-id").first()
        return Response({"kind": kind, "ref": t.ref, "amount": t.amount, "label": t.label, "item": t.item, "pending": t.pending,
                         "proof": _out(last) if last else None, "account": _acct_out(_acct())})
    return _create(request, t)


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
    qs = PayProof.objects.select_related("user").order_by("-id")
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


def _switch_on(t, txn):
    """Same as a successful gateway payment for that kind of order."""
    if t.kind == "promote":
        from shop import views as SV
        o = t.rows[0]; o.provider, o.provider_ref = "jazzcash", txn; o.save(update_fields=["provider", "provider_ref"])
        SV._activate(o)
    elif t.kind == "freelance":
        from market import views as MV
        o = t.rows[0]; o.provider, o.provider_ref = "jazzcash", txn; o.save(update_fields=["provider", "provider_ref"])
        MV._activate(o, "Paid by JazzCash, TID %s" % txn)
    elif t.kind == "store":
        from store import views as STV
        for o in t.rows:
            o.provider, o.provider_ref = "jazzcash", txn; o.save(update_fields=["provider", "provider_ref"])
            STV._paid(o)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_act(request, pid, act):
    if not _staff(request.user):
        return _err("Staff only.", 403)
    p = PayProof.objects.filter(pk=pid).select_related("user").first()
    if not p:
        return _err("Not found.", 404)
    if p.status != PayProof.PENDING:
        return _err("Already decided.")
    t = _target_of(p)
    try:
        from notifications.views import notify
    except Exception:
        notify = None
    if act == "approve":
        if not t:
            return _err("The order was removed.")
        if not t.pending:
            return _err("The order is %s, not waiting for payment." % ", ".join(sorted(set(r.status for r in t.rows))))
        _switch_on(t, p.txn)
        p.status = PayProof.APPROVED
        if notify:
            msg = {"promote": "Payment received ✓ Your order %s is active now. Thank you!",
                   "freelance": "Payment received ✓ %s is paid. The seller has started.",
                   "store": "Payment received ✓ %s is paid. The shop will send it soon."}[p.kind] % t.label.replace("Promote order ", "")
            notify(p.user, "payment", msg, ("/receipt?order=%s" % p.ref) if p.kind == "promote" else t.link)
    elif act == "reject":
        reason = re.sub(r"\s+", " ", str(request.data.get("reason") or "")).strip()[:200]
        if len(reason) < 4:
            return _err("Write why (the buyer sees it).")
        p.status, p.reason = PayProof.REJECTED, reason
        if notify:
            notify(p.user, "payment", "We could not confirm your payment for %s: %s. Please check and send it again." % (t.label if t else "your order", reason),
                   t.link if t else "/")
    else:
        return _err("Unknown action.")
    p.decided_by, p.decided_at = request.user, timezone.now()
    p.save(update_fields=["status", "reason", "decided_by", "decided_at"])
    return Response(_out(p, True))
