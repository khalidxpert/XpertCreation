"""Private API for @DamaAcademyBot (setup_lwe_academy_v1). Every bot call is signed with TGACADEMY_SECRET (HMAC-SHA256
of the body, timestamp inside, 5 minutes). /go/<token> is the one-time "Start learning" link."""
import hashlib
import hmac
import json
import re
import secrets
import string
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from academy.models import Course

from .models import Enrollment, LoginTicket, TgLink

User = get_user_model()
SITE = "https://xpertcreation.com"


def _env(k, d=""):
    try:
        from xpertapi.settings import env
        return env(k, d)
    except Exception:  # noqa: BLE001
        import os
        return os.environ.get(k, d)


def _err(msg, code=400):
    return JsonResponse({"detail": msg}, status=code)


def _signed(request):
    secret = _env("TGACADEMY_SECRET", "")
    if not secret or request.method != "POST":
        return None
    raw = request.body or b""
    want = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, request.headers.get("X-TG-Sign", "")):
        return None
    try:
        d = json.loads(raw)
    except ValueError:
        return None
    if abs(time.time() - int(d.get("ts") or 0)) > 300 or not str(d.get("tg_id", "")).lstrip("-").isdigit():
        return None
    return d


def _course_url(slug):
    return _env("TGACADEMY_COURSE_URL", "/academy/?course={slug}").replace("{slug}", slug)


def _ticket(user, next_url):
    tok = secrets.token_urlsafe(24)
    LoginTicket.objects.filter(user=user, expires__lt=timezone.now()).delete()
    LoginTicket.objects.create(user=user, token_hash=hashlib.sha256(tok.encode()).hexdigest(), next_url=next_url[:200],
                               expires=timezone.now() + timedelta(days=7))
    return SITE + "/api/tgacademy/go/" + tok


def _free_username(want, tg_id):
    try:
        mx = User._meta.get_field("username").max_length or 20
    except Exception:  # noqa: BLE001
        mx = 20
    base = re.sub(r"[^a-z0-9_]", "", (want or "").lower())[:mx]
    for cand in ([base] if len(base) >= 3 else []) + [(base or "dama")[:mx - 3] + "_tg", ("tg%d" % tg_id)[:mx]]:
        if not User.objects.filter(username__iexact=cand).exists():
            return cand
    return ("tg%d" % tg_id)[:mx - 5] + "_" + secrets.token_hex(2)


def _user_for(d, create):
    """(user, password-if-new). Finds the account linked to this Telegram id, or makes one."""
    tg_id = int(d["tg_id"])
    link = TgLink.objects.select_related("user").filter(tg_id=tg_id).first()
    if link:
        if d.get("username") and link.tg_username != d["username"]:
            TgLink.objects.filter(pk=link.pk).update(tg_username=str(d["username"])[:64])
        return link.user, ""
    if not create:
        return None, ""
    pw = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
    with transaction.atomic():
        user = User.objects.create_user(email="tg%d@users.telegram.invalid" % tg_id, password=pw,
                                        full_name=str(d.get("name") or d.get("username") or "Dama learner")[:60],
                                        username=_free_username(d.get("username"), tg_id))
        fields = []
        for f, v in (("is_email_verified", True), ("signup_country", "")):
            if hasattr(user, f):
                setattr(user, f, v); fields.append(f)
        if fields:
            user.save(update_fields=fields)
        TgLink.objects.create(user=user, tg_id=tg_id, tg_username=str(d.get("username") or "")[:64])
    return user, pw


@csrf_exempt
def provision(request):
    d = _signed(request)
    if d is None:
        return _err("Not allowed.", 403)
    course = Course.objects.filter(slug=str(d.get("course") or "")).first()
    if not course:
        return _err("Unknown course.", 404)
    order = str(d.get("order") or "")[:40]
    if not order:
        return _err("Order missing.")
    try:
        user, pw = _user_for(d, True)
    except IntegrityError:
        user, pw = _user_for(d, False)
    if not user:
        return _err("Could not create the account.", 500)
    if not Enrollment.objects.filter(order_id=order).exists():
        Enrollment.objects.get_or_create(user=user, course=course, defaults={"order_id": order})
    return JsonResponse({"username": user.username or "", "email": user.email if pw else "", "password": pw,
                         "course_title": course.title, "login_url": _ticket(user, _course_url(course.slug))})


@csrf_exempt
def link(request):
    d = _signed(request)
    if d is None:
        return _err("Not allowed.", 403)
    user, _ = _user_for(d, False)
    if not user:
        return JsonResponse({"login_url": ""})
    courses = list(Enrollment.objects.filter(user=user).select_related("course").values_list("course__title", flat=True))
    first = Enrollment.objects.filter(user=user).select_related("course").order_by("-created").first()
    return JsonResponse({"username": user.username or "", "courses": courses,
                         "login_url": _ticket(user, _course_url(first.course.slug) if first else "/academy/")})


def go(request, token):
    t = LoginTicket.objects.select_related("user").filter(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not t or t.used or t.expires < timezone.now() or getattr(t.user, "is_blocked", False) or not t.user.is_active:
        return HttpResponseRedirect("/login?tg=expired")
    LoginTicket.objects.filter(pk=t.pk, used__isnull=True).update(used=timezone.now())
    login(request, t.user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.cycle_key()
    nxt = t.next_url if t.next_url.startswith("/") and not t.next_url.startswith("//") else "/academy/"
    return HttpResponseRedirect(nxt)
