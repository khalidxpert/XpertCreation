"""XpertAcademy paid courses (setup_academy_pay_v1): access list, buy, coupons, coupon requests, team tools.
/api/tgacademy/access/                GET   paywall on?, price, which courses I may open
/api/tgacademy/buy/<slug>/            POST  start a purchase (Safepay or JazzCash, through the site's shop)
/api/tgacademy/redeem/                POST  {code, course} use a coupon
/api/tgacademy/ask/                   POST  {course, message} ask the admins for a free coupon
/api/tgacademy/team/                  GET   requests + coupons + paywall (super admin)
/api/tgacademy/team/coupon/           POST  {course|"", max_uses, days, note, user} create a coupon
/api/tgacademy/team/coupon/<id>/off/  POST  switch a coupon off
/api/tgacademy/team/ask/<id>/<act>/   POST  grant (makes a one-person coupon and sends it) | decline
/api/tgacademy/team/paywall/          POST  {on}"""
import re
import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from academy.models import Course

from .access import can_open, open_ids, paywall
from .models import Coupon, CouponRequest, CouponUse

URDU_ASK = "فیس ادا نہیں کر سکتے؟ مفت کوپن کوڈ کے لیے ایڈمن سے درخواست کریں۔"


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _super(u):
    return bool(u and u.is_authenticated and u.is_superuser)


def _name(u):
    return (getattr(u, "full_name", "") or getattr(u, "username", "") or u.email or "Member").strip()


def _price():
    try:
        from shop.views import price
        return price("course", "life")
    except Exception:  # noqa: BLE001
        return 4200


def _notify(user, msg, link):
    try:
        from notifications.views import notify
        notify(user, "academy", msg, link)
    except Exception:  # noqa: BLE001
        pass


def _notify_admins(msg, link):
    try:
        from notifications.views import notify_admins
        notify_admins("academy", msg, link)
    except Exception:  # noqa: BLE001
        pass


@api_view(["GET"])
@permission_classes([AllowAny])
def access(request):
    pw = paywall()
    u = request.user
    ids = open_ids(u, pw) if pw.on else None
    mine, pay = {}, {}
    if u.is_authenticated:
        mine = {r.course_id: r.status for r in CouponRequest.objects.filter(user=u).order_by("id")}
        try:   # JazzCash payments sent for a course: the latest one per course (pending / rejected)
            from payproof.models import PayProof
            for p in PayProof.objects.filter(user=u, order__product="course").select_related("order").order_by("id"):
                pay[p.order.target_id] = {"status": p.status, "txn": p.txn, "when": p.created_at.isoformat(), "reason": p.reason}
        except Exception:  # noqa: BLE001
            pay = {}
    out = {}
    for c in Course.objects.filter(is_active=True):
        is_open = (not pw.on) or (c.id in ids)
        out[c.slug] = {"open": is_open, "asked": mine.get(c.id, "")}
        if not is_open and pay.get(c.id) and pay[c.id]["status"] in ("pending", "rejected"):
            out[c.slug]["pay"] = pay[c.id]
    return Response({"paywall": pw.on, "price": _price(), "currency": "PKR", "usd": 15, "signed_in": u.is_authenticated,
                     "courses": out, "ask_text": {"en": "Can't pay? Ask the admin for a free coupon code.", "ur": URDU_ASK}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def buy(request, slug):
    """A shop order for this course. Pay by card/wallet (Safepay) or by JazzCash/Raast with the TID (team checks it)."""
    c = Course.objects.filter(slug=slug, is_active=True).first()
    if not c:
        return _err("Unknown course.", 404)
    u = request.user
    if can_open(u, c):
        return _err("This course is already open for you.")
    from shop import views as SV
    from shop.models import Order
    s = SV.setting()
    if not (s.mode in ("live", "manual") or (s.mode == "test" and SV._staff(u))):
        return _err("Course payments are not open yet. Ask the admin for a coupon.", 403)
    old = Order.objects.filter(user=u, product="course", target_id=c.id, status="pending").order_by("-id").first()
    if old:
        old.status = "cancelled"; old.note = "replaced by a new checkout"; old.save(update_fields=["status", "note"])
    o = Order.objects.create(user=u, product="course", plan="life", target_id=c.id, target_label=c.title[:160],
                             amount=SV.price("course", "life", s), provider="test" if s.mode == "test" else ("jazzcash" if s.mode == "manual" else ""))
    out = {"order": SV._out(o), "amount": o.amount, "checkout": "", "jazzcash": False}
    try:
        from payproof.views import _acct
        out["jazzcash"] = bool(_acct().enabled)
    except Exception:  # noqa: BLE001
        pass
    if SV.sp_ready() and s.mode == "live":
        try:
            tracker, url = SV.sp3_start(o)
            o.provider, o.provider_ref = "safepay-" + SV._sp3()["env"], tracker
            o.save(update_fields=["provider", "provider_ref"])
            out["checkout"] = url
        except Exception:  # noqa: BLE001
            pass
    if not out["checkout"] and not out["jazzcash"]:
        o.status = "cancelled"; o.save(update_fields=["status"])
        return _err("Payments are not available right now. Please try again later.", 503)
    return Response(out, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def redeem(request):
    code = re.sub(r"[^A-Z0-9-]", "", str(request.data.get("code") or "").upper())[:24]
    c = Course.objects.filter(slug=str(request.data.get("course") or ""), is_active=True).first()
    if not c:
        return _err("Choose a course.")
    if can_open(request.user, c):
        return _err("This course is already open for you.")
    cp = Coupon.objects.filter(code=code, active=True).first()
    if not cp or (cp.expires and cp.expires < timezone.now()) or cp.uses >= cp.max_uses:
        return _err("This coupon code is not valid or is used up.")
    if cp.course_id and cp.course_id != c.id:
        return _err("This coupon is for another course: %s." % cp.course.title)
    if cp.for_user_id and cp.for_user_id != request.user.id:
        return _err("This coupon was made for another member.")
    with transaction.atomic():
        n = Coupon.objects.filter(pk=cp.pk, uses__lt=F("max_uses")).update(uses=F("uses") + 1)
        if not n:
            return _err("This coupon is used up.")
        try:
            CouponUse.objects.create(coupon=cp, user=request.user, course=c)
        except IntegrityError:
            return _err("This course is already open for you.")
    CouponRequest.objects.filter(user=request.user, course=c, status=CouponRequest.OPEN).update(status=CouponRequest.GRANTED, coupon=cp, decided=timezone.now())
    return Response({"ok": True, "course": c.slug, "title": c.title})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask(request):
    c = Course.objects.filter(slug=str(request.data.get("course") or ""), is_active=True).first()
    if not c:
        return _err("Choose a course.")
    if can_open(request.user, c):
        return _err("This course is already open for you.")
    if CouponRequest.objects.filter(user=request.user, course=c, status=CouponRequest.OPEN).exists():
        return _err("You already asked for this course. The admin will reply soon.")
    if CouponRequest.objects.filter(user=request.user, created__gt=timezone.now() - timedelta(days=1)).count() >= 3:
        return _err("You can ask for 3 courses a day.")
    msg = re.sub(r"\s+", " ", str(request.data.get("message") or "")).strip()[:400]
    CouponRequest.objects.create(user=request.user, course=c, message=msg)
    _notify_admins("🎟 Coupon request: %s asks for a free coupon for %s." % (_name(request.user), c.title), "/academy/admin.html")
    return Response({"ok": True})


def _coupon_out(cp):
    return {"id": cp.id, "code": cp.code, "course": cp.course.title if cp.course_id else "Any course", "max_uses": cp.max_uses, "uses": cp.uses,
            "expires": cp.expires.isoformat() if cp.expires else "", "active": cp.active, "note": cp.note,
            "for": _name(cp.for_user) if cp.for_user_id else "", "created": cp.created.isoformat()}


def _new_code():
    for _ in range(20):
        code = "XA-" + "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        if not Coupon.objects.filter(code=code).exists():
            return code
    return "XA-" + secrets.token_hex(5).upper()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    if not _super(request.user):
        return _err("Super admin only.", 403)
    reqs = CouponRequest.objects.select_related("user", "course", "coupon").order_by("-id")[:200]
    return Response({"paywall": paywall().on, "price": _price(),
                     "courses": [{"slug": c.slug, "title": c.title} for c in Course.objects.filter(is_active=True).order_by("order")],
                     "requests": [{"id": r.id, "user": _name(r.user), "username": r.user.username or "", "email": r.user.email, "course": r.course.title,
                                   "slug": r.course.slug, "message": r.message, "status": r.status, "code": r.coupon.code if r.coupon_id else "",
                                   "created": r.created.isoformat()} for r in reqs],
                     "coupons": [_coupon_out(cp) for cp in Coupon.objects.select_related("course", "for_user").order_by("-id")[:300]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_coupon(request):
    if not _super(request.user):
        return _err("Super admin only.", 403)
    d = request.data
    course = None
    if d.get("course"):
        course = Course.objects.filter(slug=str(d["course"])).first()
        if not course:
            return _err("Unknown course.")
    try:
        uses = max(1, min(10000, int(d.get("max_uses") or 1)))
        days = max(0, min(3650, int(d.get("days") or 0)))
    except (TypeError, ValueError):
        return _err("Uses and days must be numbers.")
    code = re.sub(r"[^A-Z0-9-]", "", str(d.get("code") or "").upper())[:24] or _new_code()
    if len(code) < 4 or Coupon.objects.filter(code=code).exists():
        return _err("That code is taken or too short.")
    cp = Coupon.objects.create(code=code, course=course, max_uses=uses, expires=timezone.now() + timedelta(days=days) if days else None,
                               note=str(d.get("note") or "")[:120], created_by=request.user)
    return Response(_coupon_out(cp))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_coupon_off(request, pk):
    if not _super(request.user):
        return _err("Super admin only.", 403)
    Coupon.objects.filter(pk=pk).update(active=False)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_ask(request, pk, act):
    if not _super(request.user):
        return _err("Super admin only.", 403)
    r = CouponRequest.objects.select_related("user", "course").filter(pk=pk, status=CouponRequest.OPEN).first()
    if not r:
        return _err("Request not found or already answered.", 404)
    if act == "grant":
        cp = Coupon.objects.create(code=_new_code(), course=r.course, max_uses=1, for_user=r.user, note="request #%d" % r.id,
                                   expires=timezone.now() + timedelta(days=30), created_by=request.user)
        r.status, r.coupon, r.decided = CouponRequest.GRANTED, cp, timezone.now()
        r.save(update_fields=["status", "coupon", "decided"])
        _notify(r.user, "🎟 Your free coupon for %s: %s — open the course and tap 'I have a coupon'. (Valid 30 days)" % (r.course.title, cp.code),
                "/academy/")
        return Response({"ok": True, "code": cp.code})
    if act == "decline":
        r.status, r.decided = CouponRequest.DECLINED, timezone.now()
        r.save(update_fields=["status", "decided"])
        _notify(r.user, "Sorry, we could not give a free coupon for %s this time." % r.course.title, "/academy/")
        return Response({"ok": True})
    return _err("Unknown action.")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_paywall(request):
    if not _super(request.user):
        return _err("Super admin only.", 403)
    pw = paywall()
    on = str(request.data.get("on")).lower() in ("true", "1")
    if on and not pw.on:
        pw.started = timezone.now()        # members who started before switching on keep their courses
    pw.on = on
    pw.save()
    return Response({"paywall": pw.on})
