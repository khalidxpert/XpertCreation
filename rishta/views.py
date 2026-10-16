"""/api/rishta/... Halal Rishta. Rules:
 - Only ID-verified members (approved KYC; staff too) can make a profile. The person must be 18 or older.
 - Men see women's profiles and women see men's. Blocked and hidden profiles never show.
 - Photos: everyone sees a blurred copy. The clear photo is shown only after both sides accept (and to our team).
 - Contact (wali / parent name and phone) is never shown to members: on a match, our matchmaker calls both families.
 - Paid 'Rishta boost' (shop item rishta_boost) shows a profile first."""
import io
import os
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import models as M
from .models import Block, Case, Interest, Profile, Report

User = get_user_model()
PRIVATE = os.path.join(str(settings.BASE_DIR), "private", "rishta")
INTERESTS_PER_DAY = 10
PAGE = 20
FIELDS_TXT = {"name": 40, "city": 60, "country": 60, "education_detail": 80, "profession": 80, "languages": 80,
              "about": 1000, "family": 800, "looking_for": 800, "contact_name": 60, "contact_relation": 30, "contact_phone": 24}
FIELDS_CH = {"for_whom": M.FOR_WHOM, "gender": M.GENDER, "marital": M.MARITAL, "children": M.CHILDREN, "sect": M.SECT,
             "prayer": M.PRAYER, "education": M.EDU}


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    return re.sub(r"[ \t]+", " ", str(v or "")).strip()[:n]


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _mod(u):
    return _staff(u) or bool(u and u.is_authenticated and getattr(u, "is_moderator", False))


def _verified(u):
    if not (u and u.is_authenticated):
        return False
    if _staff(u):
        return True
    try:
        from companies.models import PersonKyc
        return PersonKyc.objects.filter(user_id=u.pk, status="approved").exists()
    except Exception:
        return False


def _notify(u, text, link="/rishta"):
    try:
        from notifications.views import notify
        notify(u, "social", text[:200], link)
    except Exception:
        pass


def _mods():
    q = Q(is_superuser=True) | Q(is_staff=True)
    if any(f.name == "is_moderator" for f in User._meta.get_fields()):
        q |= Q(is_moderator=True)
    return User.objects.filter(q, is_active=True)


def _boosted():
    try:
        from shop.models import Order
        now = timezone.now()
        return set(Order.objects.filter(product="rishta_boost", status="paid", starts_at__lte=now, ends_at__gt=now).values_list("target_id", flat=True))
    except Exception:
        return set()


def _mine(u):
    return Profile.objects.filter(user=u).first() if u and u.is_authenticated else None


def _age(p):
    return timezone.now().year - p.birth_year


def _label(choices, v):
    return dict(choices).get(v, "")


def _matched(a, b):
    """True if a and b have an accepted interest either way."""
    if not a or not b:
        return False
    return Interest.objects.filter(status="accepted").filter(Q(sender=a, receiver=b) | Q(sender=b, receiver=a)).exists()


def _card(p, viewer=None, full=False, boosted=None, clear=False):
    d = {"id": p.id, "name": p.name, "age": _age(p), "gender": p.gender, "city": p.city, "country": p.country,
         "marital": _label(M.MARITAL, p.marital), "education": _label(M.EDU, p.education), "education_detail": p.education_detail,
         "profession": p.profession, "sect": _label(M.SECT, p.sect), "for_whom": _label(M.FOR_WHOM, p.for_whom),
         "height_cm": p.height_cm, "boosted": bool(boosted and p.user_id in boosted), "verified": True,
         "photo": "", "photo_clear": False}
    if p.photo_blur and p.show_photo:
        d["photo"] = settings.MEDIA_URL + p.photo_blur
    if clear and p.photo_clear and p.show_photo:
        d["photo"], d["photo_clear"] = "/api/rishta/photo/%d/?t=%d" % (p.id, int(p.updated_at.timestamp())), True
    if full:
        d.update({"about": p.about, "family": p.family, "looking_for": p.looking_for, "languages": p.languages,
                  "prayer": _label(M.PRAYER, p.prayer), "children": _label(M.CHILDREN, p.children)})
    return d


def _own(p):
    d = _card(p, full=True, clear=True)
    for k in list(FIELDS_TXT) + list(FIELDS_CH):
        d[k] = getattr(p, k)
    d.update({"birth_year": p.birth_year, "height_cm": p.height_cm, "show_photo": p.show_photo, "status": p.status,
              "has_photo": bool(p.photo_clear)})
    return d


@api_view(["GET"])
@permission_classes([AllowAny])
def config(request):
    u = request.user
    p = _mine(u)
    return Response({"signed_in": u.is_authenticated, "verified": _verified(u), "mod": _mod(u),
                     "me": _own(p) if p else None,
                     "choices": {k: v for k, v in FIELDS_CH.items()}, "min_year": timezone.now().year - 80, "max_year": timezone.now().year - 18,
                     "count": Profile.objects.filter(status="active").count()})


def _apply(p, d, creating):
    for k, n in FIELDS_TXT.items():
        if k in d:
            setattr(p, k, _txt(d.get(k), n))
    for k, ch in FIELDS_CH.items():
        if k in d and str(d.get(k)) in dict(ch):
            if k == "gender" and not creating:
                continue                          # gender cannot change after the profile is made
            setattr(p, k, str(d.get(k)))
    if "birth_year" in d:
        try:
            p.birth_year = int(d.get("birth_year"))
        except Exception:
            pass
    if "height_cm" in d:
        try:
            h = int(d.get("height_cm") or 0); p.height_cm = h if 120 <= h <= 230 else None
        except Exception:
            p.height_cm = None
    if "show_photo" in d:
        p.show_photo = str(d.get("show_photo")).lower() in ("1", "true", "yes", "on")
    if "status" in d and p.status != "removed" and d.get("status") in ("active", "hidden"):
        p.status = d.get("status")


def _problem(p):
    y = timezone.now().year
    if not p.name or len(p.name) < 2:
        return "Write a name (first name is enough)."
    if p.gender not in ("M", "F"):
        return "Choose man or woman."
    if not p.birth_year or p.birth_year > y - 18:
        return "The person must be 18 or older."
    if p.birth_year < y - 80:
        return "Check the year of birth."
    if not p.city:
        return "Write the city."
    if not re.fullmatch(r"\+?[0-9 \-]{10,20}", p.contact_phone or ""):
        return "Write a phone number for our matchmaker (wali or parent). Only our team sees it."
    if not p.contact_name:
        return "Write the name of the person our matchmaker should call (wali or parent)."
    return ""


@api_view(["POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def me(request):
    u = request.user
    p = _mine(u)
    if request.method == "DELETE":
        if p:
            for f in (p.photo_clear and os.path.join(PRIVATE, p.photo_clear), p.photo_blur and os.path.join(str(settings.MEDIA_ROOT), p.photo_blur)):
                if f and os.path.exists(f):
                    os.remove(f)
            p.delete()
        return Response({"ok": True})
    if not p:
        if not _verified(u):
            return _err("Only members with a verified ID can make a rishta profile. Verify your ID first on /get-verified.", 403)
        p = Profile(user=u, birth_year=0)
        _apply(p, request.data, True)
    else:
        _apply(p, request.data, False)
    bad = _problem(p)
    if bad:
        return _err(bad)
    p.save()
    return Response({"me": _own(p)})


def _save_photo(p, f):
    from PIL import Image, ImageFilter, ImageOps
    if f.size > 8 * 1048576:
        raise ValueError("Photo up to 8 MB.")
    im = Image.open(f)
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((900, 900))
    os.makedirs(PRIVATE, exist_ok=True)
    clear = "%d-%s.webp" % (p.user_id, secrets.token_hex(8))
    im.save(os.path.join(PRIVATE, clear), "WEBP", quality=82)          # re-saved: no phone location data kept
    sm = im.copy(); sm.thumbnail((360, 360))
    sm = sm.filter(ImageFilter.GaussianBlur(radius=max(14, sm.width // 14)))
    rel = "rishta/%s.webp" % secrets.token_hex(12)
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    sm.save(full, "WEBP", quality=60)
    for old in (p.photo_clear and os.path.join(PRIVATE, p.photo_clear), p.photo_blur and os.path.join(str(settings.MEDIA_ROOT), p.photo_blur)):
        if old and os.path.exists(old):
            os.remove(old)
    p.photo_clear, p.photo_blur = clear, rel
    p.save()


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def photo_upload(request):
    p = _mine(request.user)
    if not p:
        return _err("Make your profile first.")
    if request.method == "DELETE":
        for old in (p.photo_clear and os.path.join(PRIVATE, p.photo_clear), p.photo_blur and os.path.join(str(settings.MEDIA_ROOT), p.photo_blur)):
            if old and os.path.exists(old):
                os.remove(old)
        p.photo_clear = p.photo_blur = ""; p.save()
        return Response({"me": _own(p)})
    f = request.FILES.get("photo")
    if not f:
        return _err("Choose a photo.")
    try:
        _save_photo(p, f)
    except ValueError as e:
        return _err(str(e))
    except Exception:
        return _err("Could not read that photo. Try a JPG or PNG.")
    return Response({"me": _own(p)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def photo(request, pid):
    """The clear photo: for the owner, our team, and the other side of an accepted interest only."""
    p = Profile.objects.filter(pk=pid).first()
    if not p or not p.photo_clear:
        raise Http404
    u = request.user
    if not (p.user_id == u.pk or _mod(u) or (p.show_photo and _matched(_mine(u), p))):
        return _err("This photo is shown only after both sides accept.", 403)
    path = os.path.join(PRIVATE, p.photo_clear)
    if not os.path.exists(path):
        raise Http404
    r = FileResponse(open(path, "rb"), content_type="image/webp")
    r["Cache-Control"] = "private, max-age=3600"
    return r


def _hidden_ids(p):
    """Profiles this member must not see: blocked either way."""
    a = set(Block.objects.filter(by=p).values_list("who_id", flat=True))
    b = set(Block.objects.filter(who=p).values_list("by_id", flat=True))
    return a | b


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def browse(request):
    me_p = _mine(request.user)
    if not me_p or me_p.status != "active":
        return _err("Make your profile first (or show it again) to see rishtay.", 403)
    q = Profile.objects.filter(status="active").exclude(pk=me_p.pk).exclude(gender=me_p.gender).exclude(pk__in=_hidden_ids(me_p))
    g = request.GET
    y = timezone.now().year
    try:
        if g.get("age_min"):
            q = q.filter(birth_year__lte=y - int(g["age_min"]))
        if g.get("age_max"):
            q = q.filter(birth_year__gte=y - int(g["age_max"]))
    except ValueError:
        pass
    if g.get("city"):
        q = q.filter(city__icontains=_txt(g["city"], 60))
    for k in ("marital", "sect", "education"):
        if g.get(k):
            q = q.filter(**{k: g[k]})
    if g.get("q"):
        t = _txt(g["q"], 60)
        q = q.filter(Q(profession__icontains=t) | Q(education_detail__icontains=t) | Q(about__icontains=t) | Q(name__icontains=t))
    boosted = _boosted()
    pairs = list(q.order_by("-updated_at").values_list("id", "user_id")[:1000])
    pairs.sort(key=lambda x: 0 if x[1] in boosted else 1)
    ids = [x[0] for x in pairs]
    try:
        page = max(1, int(g.get("page", 1)))
    except ValueError:
        page = 1
    chunk = ids[(page - 1) * PAGE: page * PAGE]
    rows = {p.id: p for p in Profile.objects.filter(id__in=chunk)}
    sent = dict(Interest.objects.filter(sender=me_p, receiver_id__in=chunk).values_list("receiver_id", "status"))
    got = dict(Interest.objects.filter(receiver=me_p, sender_id__in=chunk).values_list("sender_id", "status"))
    out = []
    for i in chunk:
        p = rows.get(i)
        if not p:
            continue
        c = _card(p, boosted=boosted, clear=(sent.get(i) == "accepted" or got.get(i) == "accepted"))
        c["sent"], c["got"] = sent.get(i, ""), got.get(i, "")
        out.append(c)
    return Response({"items": out, "total": len(ids), "page": page, "pages": (len(ids) + PAGE - 1) // PAGE})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail(request, pid):
    me_p = _mine(request.user)
    p = Profile.objects.filter(pk=pid).first()
    mod = _mod(request.user)
    if not p or (not mod and (not me_p or p.status != "active" or p.gender == (me_p.gender if me_p else "") or p.pk in _hidden_ids(me_p))):
        return _err("This profile is not available.", 404)
    m = _matched(me_p, p)
    d = _card(p, full=True, boosted=_boosted(), clear=m or mod)
    d["sent"] = Interest.objects.filter(sender=me_p, receiver=p).values_list("status", flat=True).first() or "" if me_p else ""
    d["got"] = Interest.objects.filter(sender=p, receiver=me_p).values_list("status", flat=True).first() or "" if me_p else ""
    d["matched"] = m
    return Response(d)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_interest(request, pid):
    me_p = _mine(request.user)
    if not me_p or me_p.status != "active":
        return _err("Make your profile first.", 403)
    p = Profile.objects.filter(pk=pid, status="active").first()
    if not p or p.gender == me_p.gender or p.pk in _hidden_ids(me_p):
        return _err("This profile is not available.", 404)
    if Interest.objects.filter(sender=me_p, created_at__gte=timezone.now() - timedelta(days=1)).count() >= INTERESTS_PER_DAY:
        return _err("You can send %d interests a day. Please try again tomorrow." % INTERESTS_PER_DAY, 429)
    back = Interest.objects.filter(sender=p, receiver=me_p).first()
    if back and back.status == "sent":
        return _err("%s already sent you an interest - accept it in Interests." % p.name)
    i, made = Interest.objects.get_or_create(sender=me_p, receiver=p, defaults={"message": _txt(request.data.get("message"), 300)})
    if not made:
        if i.status in ("withdrawn",):
            i.status, i.message, i.created_at, i.answered_at = "sent", _txt(request.data.get("message"), 300), timezone.now(), None
            i.save()
        else:
            return _err("You already sent an interest to %s." % p.name)
    _notify(p.user, "Rishta: %s (%d, %s) sent an interest for %s." % (me_p.name, _age(me_p), me_p.city, p.name), "/rishta#interests")
    return Response({"ok": True, "status": i.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answer(request, iid):
    me_p = _mine(request.user)
    i = Interest.objects.filter(pk=iid, receiver=me_p, status="sent").select_related("sender__user").first() if me_p else None
    if not i:
        return _err("This interest is not waiting for your answer.", 404)
    yes = str(request.data.get("accept")).lower() in ("1", "true", "yes")
    i.status, i.answered_at = ("accepted" if yes else "declined"), timezone.now()
    i.save()
    if yes:
        Case.objects.get_or_create(interest=i)
        _notify(i.sender.user, "Rishta: %s accepted your interest. Our matchmaker will call your family soon, in sha Allah." % me_p.name, "/rishta#interests")
        _notify(me_p.user, "Rishta: you and %s both said yes. Our matchmaker will call your family soon, in sha Allah." % i.sender.name, "/rishta#interests")
        for m in _mods():
            _notify(m, "Rishta match to call: %s and %s." % (i.sender.name, me_p.name), "/rishta#matchmaker")
    return Response({"ok": True, "status": i.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request, iid):
    me_p = _mine(request.user)
    i = Interest.objects.filter(pk=iid, sender=me_p, status="sent").first() if me_p else None
    if not i:
        return _err("Only an interest that is still waiting can be taken back.", 404)
    i.status = "withdrawn"; i.save()
    return Response({"ok": True})


def _case_status(i):
    c = getattr(i, "case", None)
    return _label(M.C_STATUS, c.status) if c else ""


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def interests(request):
    me_p = _mine(request.user)
    if not me_p:
        return Response({"received": [], "sent": [], "matches": []})
    boosted = _boosted()
    rec = Interest.objects.filter(receiver=me_p).exclude(status="withdrawn").select_related("sender").order_by("-created_at")[:100]
    snt = Interest.objects.filter(sender=me_p).exclude(status="withdrawn").select_related("receiver").order_by("-created_at")[:100]
    def row(i, other):
        m = i.status == "accepted"
        return {"id": i.id, "status": i.status, "message": i.message, "when": i.created_at.isoformat(),
                "case": _case_status(i) if m else "", "p": _card(other, boosted=boosted, clear=m)}
    received = [row(i, i.sender) for i in rec if i.sender.status == "active" or i.status == "accepted"]
    sent = [row(i, i.receiver) for i in snt if i.receiver.status == "active" or i.status == "accepted"]
    return Response({"received": received, "sent": sent})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def block(request, pid):
    me_p = _mine(request.user)
    p = Profile.objects.filter(pk=pid).first()
    if not me_p or not p or p.pk == me_p.pk:
        return _err("Not possible.")
    Block.objects.get_or_create(by=me_p, who=p)
    Interest.objects.filter(Q(sender=me_p, receiver=p) | Q(sender=p, receiver=me_p), status="sent").update(status="declined")
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report(request, pid):
    p = Profile.objects.filter(pk=pid).first()
    reason = _txt(request.data.get("reason"), 300)
    if not p or len(reason) < 5:
        return _err("Write what is wrong (a few words).")
    if Report.objects.filter(by=request.user, created_at__gte=timezone.now() - timedelta(days=1)).count() >= 10:
        return _err("Too many reports today.", 429)
    Report.objects.create(by=request.user, profile=p, reason=reason)
    for m in _mods():
        _notify(m, "Rishta report about %s: %s" % (p.name, reason[:100]), "/rishta#matchmaker")
    return Response({"ok": True})


# ---- matchmaker (moderators and staff)
def _contact(p):
    return {"id": p.id, "name": p.name, "age": _age(p), "city": p.city, "gender": p.gender, "for_whom": _label(M.FOR_WHOM, p.for_whom),
            "contact_name": p.contact_name, "contact_relation": p.contact_relation, "contact_phone": p.contact_phone,
            "member": getattr(p.user, "full_name", "") or p.user.username, "username": p.user.username}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cases(request):
    if not _mod(request.user):
        return _err("Only our team.", 403)
    st = request.GET.get("status") or ""
    q = Case.objects.select_related("interest__sender__user", "interest__receiver__user", "assigned").order_by("-updated_at")
    if st == "open":
        q = q.exclude(status__in=("nikah", "closed"))
    elif st in dict(M.C_STATUS):
        q = q.filter(status=st)
    out = [{"id": c.id, "status": c.status, "status_label": _label(M.C_STATUS, c.status), "note": c.note,
            "assigned": (getattr(c.assigned, "full_name", "") or c.assigned.username) if c.assigned else "",
            "updated": c.updated_at.isoformat(), "a": _contact(c.interest.sender), "b": _contact(c.interest.receiver)} for c in q[:200]]
    reps = [{"id": r.id, "reason": r.reason, "when": r.created_at.isoformat(), "profile": _contact(r.profile), "status": r.profile.status}
            for r in Report.objects.filter(handled=False).select_related("profile__user").order_by("-created_at")[:100]]
    return Response({"cases": out, "reports": reps, "statuses": M.C_STATUS,
                     "counts": {"open": Case.objects.exclude(status__in=("nikah", "closed")).count(), "nikah": Case.objects.filter(status="nikah").count(),
                                "profiles": Profile.objects.filter(status="active").count()}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def case_update(request, cid):
    if not _mod(request.user):
        return _err("Only our team.", 403)
    c = Case.objects.filter(pk=cid).select_related("interest__sender__user", "interest__receiver__user").first()
    if not c:
        return _err("Not found.", 404)
    d = request.data
    if d.get("status") in dict(M.C_STATUS) and d.get("status") != c.status:
        c.status = d["status"]
        if c.status == "nikah":
            for p in (c.interest.sender, c.interest.receiver):
                _notify(p.user, "Rishta: Mubarak! May Allah bless this nikah. Thank you for trusting XpertCreation.", "/rishta")
    if "note" in d:
        c.note = str(d.get("note") or "")[:4000]
    if d.get("assign_me"):
        c.assigned = request.user
    c.save()
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def moderate(request, pid):
    """Our team: remove or restore a profile, and close its reports."""
    if not _mod(request.user):
        return _err("Only our team.", 403)
    p = Profile.objects.filter(pk=pid).first()
    if not p:
        return _err("Not found.", 404)
    act = request.data.get("action")
    if act == "remove":
        p.status = "removed"; p.save()
        _notify(p.user, "Rishta: your profile was taken down by our team. Reply in Support (/tickets) if you think this is a mistake.", "/tickets")
    elif act == "restore":
        p.status = "active"; p.save()
    Report.objects.filter(profile=p).update(handled=True)
    return Response({"ok": True, "status": p.status})
