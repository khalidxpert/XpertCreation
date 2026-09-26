"""Find people you know: a member picks contacts on their phone (or types emails and numbers), and we
say which of them are on XpertCreation. Only members who allow it can be found, the list is checked in
memory and thrown away, and the number of checks per day is limited so nobody can use it to trawl."""
import re

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FindSetting

User = get_user_model()
MAX_PER_CHECK = 300
CHECKS_PER_DAY = 5
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,24}$", re.I)


def _digits(p):
    """Last 10 digits of a phone number, so 0300-1234567, +92 300 1234567 and 923001234567 all match."""
    d = re.sub(r"\D", "", str(p or ""))
    return d[-10:] if len(d) >= 10 else ""


def _phone_map():
    """last-10-digits -> user id, from the phone and WhatsApp numbers members put on their profiles."""
    m = cache.get("find:phones")
    if m is not None:
        return m
    m = {}
    try:
        from network.models import ProProfile
        for uid, socials in ProProfile.objects.values_list("user_id", "socials"):
            if isinstance(socials, dict):
                for k, v in socials.items():
                    if any(w in str(k).lower() for w in ("whatsapp", "phone", "signal", "telegram")):
                        d = _digits(v)
                        if d:
                            m[d] = uid
    except Exception:
        pass
    for f in ("phone", "phone_number", "mobile"):
        if any(x.name == f for x in User._meta.get_fields()):
            for uid, ph in User.objects.exclude(**{f: ""}).exclude(**{f + "__isnull": True}).values_list("id", f):
                d = _digits(ph)
                if d:
                    m[d] = uid
    cache.set("find:phones", m, 600)
    return m


def _card(u):
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).first()
    except Exception:
        p = None
    try:
        from network.views import _av
        av = _av(u) or ""
    except Exception:
        av = ""
    return {"id": u.id, "name": (getattr(u, "full_name", "") or "").strip() or "Member", "avatar": av,
            "slug": p.slug if p else None, "headline": p.headline if p else ""}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contacts(request):
    """body: {emails: [...], phones: [...]} -> the members among them who can be found."""
    key = "find:checks:%d:%s" % (request.user.pk, timezone.localdate())
    n = cache.get(key, 0)
    if n >= CHECKS_PER_DAY:
        return Response({"detail": "You can check contacts %d times a day. Try again tomorrow." % CHECKS_PER_DAY}, status=429)
    emails = {str(e).strip().lower() for e in (request.data.get("emails") or [])[:MAX_PER_CHECK] if EMAIL.match(str(e).strip())}
    phones = {_digits(p) for p in (request.data.get("phones") or [])[:MAX_PER_CHECK]} - {""}
    if not emails and not phones:
        return Response({"detail": "No email addresses or phone numbers to check."}, status=400)
    cache.set(key, n + 1, 90000)
    off_email = set(FindSetting.objects.filter(by_email=False).values_list("user_id", flat=True))
    off_phone = set(FindSetting.objects.filter(by_phone=False).values_list("user_id", flat=True))
    ids = set()
    if emails:
        from django.db.models.functions import Lower
        ids |= set(User.objects.annotate(_le=Lower("email")).filter(_le__in=list(emails), is_active=True).values_list("id", flat=True)) - off_email
    if phones:
        pm = _phone_map()
        ids |= {pm[d] for d in phones if d in pm} - off_phone
    ids.discard(request.user.id)
    users = User.objects.filter(id__in=ids, is_active=True)
    if any(f.name == "is_blocked" for f in User._meta.get_fields()):
        users = users.filter(is_blocked=False)
    found = [_card(u) for u in users[:MAX_PER_CHECK]]
    return Response({"found": sorted(found, key=lambda x: x["name"].lower()), "checked": len(emails) + len(phones),
                     "checks_left": CHECKS_PER_DAY - n - 1})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def find_settings(request):
    s, _ = FindSetting.objects.get_or_create(user=request.user)
    if request.method == "POST":
        for f in ("by_email", "by_phone"):
            if f in request.data:
                setattr(s, f, str(request.data.get(f)).lower() in ("true", "1"))
        s.save()
    return Response({"by_email": s.by_email, "by_phone": s.by_phone})
