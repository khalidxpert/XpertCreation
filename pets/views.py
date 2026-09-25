"""Pets: profiles, health records, vaccine schedule, QR tag page, lost & found.

Everything is free. Only the owner can see or change a pet's records. The public tag
page shows only what the owner chose to show.
"""
import os
import re
import secrets
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from notifications.views import notify

from .models import SPECIES, FoundNote, HealthRecord, LostFound, Pet, VaccineTemplate

YES = (True, "true", "True", "1", 1, "on", "yes")
SPECIES_KEYS = dict(SPECIES)
MAX_PETS = 20
MAX_PHOTO = 2 * 1024 * 1024
SITE = "https://xpertcreation.com"


class _Throttle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ident = request.user.pk if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class EditThrottle(_Throttle):
    scope = "pets_edit"


class FoundThrottle(_Throttle):
    scope = "pets_found"


class LostThrottle(_Throttle):
    scope = "pets_lost"


class BrowseThrottle(_Throttle):
    scope = "pets_browse"


def _err(msg, code=400):
    return Response({"detail": msg}, status=code)


def _txt(v, n):
    return re.sub(r"[ \t]+", " ", str(v or "")).strip()[:n]


def _long(v, n):
    return str(v or "").replace("\r\n", "\n").strip()[:n]


def _phone(v):
    v = re.sub(r"[^\d+ \-()]", "", str(v or "")).strip()[:30]
    return v if len(re.sub(r"\D", "", v)) >= 7 else ""


def _date(v):
    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _name(u):
    return (getattr(u, "full_name", "") or "").strip() or "A member"


def _url(path):
    return (settings.MEDIA_URL.rstrip("/") + "/" + path) if path else ""


def _drop(path):
    if path and path.startswith("pets/") and ".." not in path:
        try:
            os.remove(os.path.join(settings.MEDIA_ROOT, path))
        except OSError:
            pass


def _save_photo(f, prefix):
    """Checked, turned upright, shrunk to 800px and saved as JPEG. Returns the media path."""
    from PIL import Image, ImageOps
    if not f:
        raise ValueError("Pick a photo.")
    if f.size > MAX_PHOTO:
        raise ValueError("That photo is over 2 MB. Pick a smaller one.")
    try:
        im = Image.open(f)
        fmt = im.format
        im.load()
    except Exception:
        raise ValueError("That file is not a photo we can read.")
    if fmt not in ("JPEG", "PNG", "WEBP"):
        raise ValueError("Use a JPG, PNG or WebP photo.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((800, 800))
    rel = "pets/%s_%s.jpg" % (prefix, secrets.token_hex(8))
    full = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "JPEG", quality=82, optimize=True)
    return rel


def _age(dob):
    if not dob:
        return ""
    today = timezone.localdate()
    months = (today.year - dob.year) * 12 + today.month - dob.month - (1 if today.day < dob.day else 0)
    if months < 0:
        return ""
    if months < 1:
        return "%d days" % (today - dob).days
    if months < 24:
        return "%d month%s" % (months, "" if months == 1 else "s")
    return "%d years" % (months // 12)


def _rec(r):
    return {"id": r.id, "kind": r.kind, "title": r.title, "notes": r.notes, "weight_kg": r.weight_kg,
            "date": r.date.isoformat() if r.date else None, "done": r.done,
            "next_due": r.next_due.isoformat() if r.next_due else None, "repeat_days": r.repeat_days}


def _pet(p, full=False):
    today = timezone.localdate()
    out = {"id": p.id, "name": p.name, "species": p.species, "breed": p.breed, "gender": p.gender,
           "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
           "age": _age(p.date_of_birth), "photo_url": _url(p.photo), "bio": p.bio,
           "tag_code": p.tag_code, "tag_url": "%s/pet/%s" % (SITE, p.tag_code),
           "contact_phone": p.contact_phone, "is_lost": p.is_lost,
           "lost_since": p.lost_since.isoformat() if p.lost_since else None,
           "due_soon": p.records.filter(next_due__isnull=False, next_due__lte=today + timedelta(days=30)).count()}
    if full:
        out["records"] = [_rec(r) for r in p.records.all()[:200]]
        out["found_notes"] = [{"message": n.message, "phone": n.phone,
                               "when": n.created_at.strftime("%d %b %Y, %H:%M")} for n in p.found_notes.all()[:20]]
    return out


def _mine(request, pk):
    return Pet.objects.filter(pk=pk, owner=request.user).first()


def _fill(p, d):
    if "name" in d:
        p.name = _txt(d.get("name"), 60)
    if "species" in d and d.get("species") in SPECIES_KEYS:
        p.species = d.get("species")
    if "breed" in d:
        p.breed = _txt(d.get("breed"), 80)
    if "gender" in d and d.get("gender") in dict(Pet.GENDERS):
        p.gender = d.get("gender")
    if "date_of_birth" in d:
        dob = _date(d.get("date_of_birth"))
        if dob and dob > timezone.localdate():
            raise ValueError("The birthday is in the future.")
        p.date_of_birth = dob
    if "bio" in d:
        p.bio = _long(d.get("bio"), 1000)
    if "contact_phone" in d:
        raw = str(d.get("contact_phone") or "").strip()
        p.contact_phone = _phone(raw)
        if raw and not p.contact_phone:
            raise ValueError("That phone number does not look right.")
    if not p.name:
        raise ValueError("Give your pet a name.")


# ---------------------------------------------------------------- owner

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def mine(request):
    if request.method == "POST":
        if Pet.objects.filter(owner=request.user).count() >= MAX_PETS:
            return _err("Twenty pets is the limit.")
        p = Pet(owner=request.user)
        try:
            _fill(p, request.data)
        except ValueError as e:
            return _err(str(e))
        for _ in range(5):                       # tag codes are random; retry on the rare clash
            try:
                p.save()
                break
            except Exception:
                p.tag_code = Pet._meta.get_field("tag_code").default()
        return Response(_pet(p, full=True), status=201)
    return Response({"pets": [_pet(p) for p in Pet.objects.filter(owner=request.user)]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def pet_detail(request, pk):
    p = _mine(request, pk)
    if not p:
        return _err("Pet not found.", 404)
    if request.method == "POST":
        try:
            _fill(p, request.data)
        except ValueError as e:
            return _err(str(e))
        p.save()
    return Response(_pet(p, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def pet_delete(request, pk):
    p = _mine(request, pk)
    if p:
        _drop(p.photo)
        p.delete()
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([EditThrottle])
def pet_photo(request, pk):
    p = _mine(request, pk)
    if not p:
        return _err("Pet not found.", 404)
    try:
        rel = _save_photo(request.FILES.get("photo"), "pet%d" % p.id)
    except ValueError as e:
        return _err(str(e))
    _drop(p.photo)
    p.photo = rel
    p.save(update_fields=["photo"])
    return Response(_pet(p, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def pet_lost(request, pk):
    p = _mine(request, pk)
    if not p:
        return _err("Pet not found.", 404)
    lost = request.data.get("lost") in YES
    p.is_lost = lost
    p.lost_since = timezone.now() if lost else None
    p.save(update_fields=["is_lost", "lost_since"])
    return Response(_pet(p, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def pet_schedule(request, pk):
    """Plan the vaccines from the templates for this species, starting from the pet's birthday."""
    p = _mine(request, pk)
    if not p:
        return _err("Pet not found.", 404)
    if not p.date_of_birth:
        return _err("Add your pet's birthday first - the schedule counts from it.")
    today = timezone.localdate()
    made = 0
    for t in VaccineTemplate.objects.filter(species=p.species):
        due = p.date_of_birth + timedelta(weeks=t.due_at_weeks)
        if due < today:
            if not t.repeat_every_days:
                continue                         # a one-off that is already past
            while due < today:
                due += timedelta(days=t.repeat_every_days)
        if p.records.filter(title=t.vaccine_name, next_due=due).exists():
            continue
        HealthRecord.objects.create(pet=p, kind="vaccine", title=t.vaccine_name, notes=t.notes,
                                    date=due, done=False, next_due=due, repeat_days=t.repeat_every_days)
        made += 1
    out = _pet(p, full=True)
    out["planned"] = made
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def record_save(request, pk):
    p = _mine(request, pk)
    if not p:
        return _err("Pet not found.", 404)
    d = request.data
    rid = d.get("id")
    r = p.records.filter(pk=rid).first() if rid else HealthRecord(pet=p)
    if rid and not r:
        return _err("That record was not found.", 404)
    if not rid and p.records.count() >= 500:
        return _err("This pet has too many records.")
    r.kind = d.get("kind") if d.get("kind") in dict(HealthRecord.KINDS) else "other"
    r.title = _txt(d.get("title"), 150)
    if not r.title:
        return _err("Give the record a title, like 'Rabies vaccine'.")
    r.notes = _long(d.get("notes"), 1000)
    try:
        w = float(d.get("weight_kg")) if d.get("weight_kg") not in (None, "") else None
    except (TypeError, ValueError):
        return _err("The weight should be a number in kg.")
    if w is not None and not (0 < w < 500):
        return _err("The weight should be between 0 and 500 kg.")
    r.weight_kg = w
    r.date = _date(d.get("date")) or timezone.localdate()
    r.next_due = _date(d.get("next_due"))
    if r.next_due and r.next_due < r.date:
        return _err("The next date is before this one.")
    r.done = True
    r.save()
    return Response(_pet(p, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def record_done(request, rid):
    """A planned vaccine was given today: mark it, and plan the next one if it repeats."""
    r = HealthRecord.objects.filter(pk=rid, pet__owner=request.user).select_related("pet").first()
    if not r:
        return _err("That record was not found.", 404)
    today = timezone.localdate()
    r.done, r.date = True, today
    r.next_due = today + timedelta(days=r.repeat_days) if r.repeat_days else None
    r.reminded_for = None
    r.save()
    return Response(_pet(r.pet, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def record_delete(request, rid):
    r = HealthRecord.objects.filter(pk=rid, pet__owner=request.user).select_related("pet").first()
    if not r:
        return _err("That record was not found.", 404)
    pet = r.pet
    r.delete()
    return Response(_pet(pet, full=True))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def upcoming(request):
    today = timezone.localdate()
    rows = (HealthRecord.objects.filter(pet__owner=request.user, next_due__isnull=False,
                                        next_due__lte=today + timedelta(days=30))
            .select_related("pet").order_by("next_due"))
    return Response({"upcoming": [{"pet_id": r.pet_id, "pet": r.pet.name, "title": r.title, "done": r.done,
                                   "record_id": r.id, "next_due": r.next_due.isoformat(),
                                   "overdue": r.next_due < today} for r in rows[:100]]})


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def templates(request, species):
    return Response({"templates": [{"vaccine": t.vaccine_name, "weeks": t.due_at_weeks,
                                    "repeat_days": t.repeat_every_days, "notes": t.notes}
                                   for t in VaccineTemplate.objects.filter(species=species)]})


# ---------------------------------------------------------------- public tag page

def _by_tag(code):
    return Pet.objects.filter(tag_code=str(code).upper()[:12]).select_related("owner").first()


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def tag(request, code):
    p = _by_tag(code)
    if not p or not p.owner.is_active:
        return _err("No pet has this tag.", 404)
    return Response({"name": p.name, "species": p.species, "breed": p.breed, "gender": p.gender,
                     "age": _age(p.date_of_birth), "photo_url": _url(p.photo), "bio": p.bio,
                     "is_lost": p.is_lost, "lost_since": p.lost_since.strftime("%d %b %Y") if p.lost_since else None,
                     "contact_phone": p.contact_phone, "owner_first_name": _name(p.owner).split()[0],
                     "is_owner": request.user.is_authenticated and request.user.pk == p.owner_id})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([FoundThrottle])
def tag_found(request, code):
    p = _by_tag(code)
    if not p or not p.owner.is_active:
        return _err("No pet has this tag.", 404)
    msg = _txt(request.data.get("message"), 500)
    if len(msg) < 5:
        return _err("Write a line about where the pet is.")
    phone = _phone(request.data.get("phone"))
    FoundNote.objects.create(pet=p, message=msg, phone=phone,
                             finder=request.user if request.user.is_authenticated else None)
    notify(p.owner, "pet", "Someone found %s: %s%s" % (p.name, msg[:120], (" - call " + phone) if phone else ""),
           "/pets#pet-%d" % p.id)
    return Response({"ok": True})


# ---------------------------------------------------------------- lost & found board

def _lf(x, viewer):
    return {"id": x.id, "kind": x.kind, "species": x.species, "title": x.title, "description": x.description,
            "photo_url": _url(x.photo), "city": x.city, "where": x.where, "contact_phone": x.contact_phone,
            "status": x.status, "when": x.created_at.strftime("%d %b %Y"),
            "tag_url": ("%s/pet/%s" % (SITE, x.pet.tag_code)) if x.pet_id and x.kind == "lost" else "",
            "mine": viewer.is_authenticated and viewer.pk == x.reporter_id}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def lost_board(request):
    now = timezone.now()
    if request.method == "POST":
        u = request.user
        if not u.is_authenticated:
            return _err("Sign in to post on the board.", 403)
        if not getattr(u, "is_email_verified", True):
            return _err("Verify your email before posting.", 403)
        if not LostThrottle().allow_request(request, None):
            return _err("You have posted a lot today. Try again later.", 429)
        d = request.data
        kind = d.get("kind")
        if kind not in ("lost", "found"):
            return _err("Is it a lost pet or a found one?")
        title = _txt(d.get("title"), 100)
        if not title:
            return _err("Add a short title, like 'Brown cat with white paws'.")
        pet = None
        if d.get("pet_id"):
            pet = Pet.objects.filter(pk=d.get("pet_id"), owner=u).first()
        x = LostFound.objects.create(
            reporter=u, pet=pet, kind=kind,
            species=d.get("species") if d.get("species") in SPECIES_KEYS else (pet.species if pet else "other"),
            title=title, description=_long(d.get("description"), 1000), city=_txt(d.get("city"), 60),
            where=_txt(d.get("where"), 200), contact_phone=_phone(d.get("contact_phone")))
        if pet and kind == "lost" and not pet.is_lost:
            pet.is_lost, pet.lost_since = True, now
            pet.save(update_fields=["is_lost", "lost_since"])
        return Response(_lf(x, u), status=201)

    qs = LostFound.objects.filter(status="active", expires_at__gt=now).select_related("pet")
    kind = request.GET.get("kind")
    if kind in ("lost", "found"):
        qs = qs.filter(kind=kind)
    city = _txt(request.GET.get("city"), 60)
    if city:
        qs = qs.filter(city__icontains=city)
    sp = request.GET.get("species")
    if sp in SPECIES_KEYS:
        qs = qs.filter(species=sp)
    if request.GET.get("mine") in YES and request.user.is_authenticated:
        qs = LostFound.objects.filter(reporter=request.user).select_related("pet")
    return Response({"reports": [_lf(x, request.user) for x in qs[:100]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([EditThrottle])
def lost_photo(request, rid):
    x = LostFound.objects.filter(pk=rid, reporter=request.user).first()
    if not x:
        return _err("That report was not found.", 404)
    try:
        rel = _save_photo(request.FILES.get("photo"), "lf%d" % x.id)
    except ValueError as e:
        return _err(str(e))
    _drop(x.photo)
    x.photo = rel
    x.save(update_fields=["photo"])
    return Response(_lf(x, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def lost_resolve(request, rid):
    x = LostFound.objects.filter(pk=rid, reporter=request.user).select_related("pet").first()
    if not x:
        return _err("That report was not found.", 404)
    x.status, x.resolved_at = "resolved", timezone.now()
    x.save(update_fields=["status", "resolved_at"])
    if x.pet_id and x.kind == "lost" and x.pet.is_lost:
        x.pet.is_lost, x.pet.lost_since = False, None
        x.pet.save(update_fields=["is_lost", "lost_since"])
    return Response(_lf(x, request.user))
