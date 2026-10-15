"""Roots of Love API (/api/roots/). Families are private: only approved members see the tree, phones, album and notices.
Anyone signed in can start a family (and becomes its admin). Others join with the family code (an admin approves)
or with an invite link from a member (no approval needed). Relations (Chacha, Phuphi, Nana...) are worked out on the page."""
import json
import os
import re
import secrets
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Family, Invite, Membership, Notice, Person, Photo

MAX_FAMILIES = 10          # families one member can start
MAX_PEOPLE = 3000
MAX_PHOTOS = 600
MAX_PIC_MB = 10
INVITE_DAYS = 14
KINDS = dict(Notice.KINDS)
LINKS = ("father", "mother", "spouse", "son", "daughter", "brother", "sister")


# ---------- helpers
def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _long(v, n):
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", str(v or "").replace("\r", ""))).strip()[:n]


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _day(v):
    v = str(v or "").strip()
    if not v:
        return None
    try:
        d = date.fromisoformat(v[:10])
    except ValueError:
        return False
    return d if date(1500, 1, 1) <= d <= date.today() + timedelta(days=3660) else False


def _phone(v):
    return re.sub(r"[^\d+]", "", str(v or ""))[:20]


def _name(u):
    return (getattr(u, "full_name", "") or getattr(u, "username", "") or "Member").strip() if u else ""


def _avatar(u):
    try:
        from accounts.views import avatar_url
        return avatar_url(u.avatar) or ""
    except Exception:
        return ""


def _media(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p else ""


def _notify(user, text, link="/roots"):
    try:
        from notifications.views import notify
        notify(user, "roots", text, link)
    except Exception:
        pass


def _code():
    abc = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        c = "RL" + "".join(secrets.choice(abc) for _ in range(6))
        if not Family.objects.filter(code=c).exists():
            return c


def _mem(fam_id, u):
    """The approved membership of this user in this family, or None."""
    if not u.is_authenticated:
        return None
    return Membership.objects.filter(family_id=fam_id, user=u).exclude(role=Membership.PENDING).select_related("family").first()


def _admin(m):
    return bool(m and m.role == Membership.ADMIN)


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _person(p, mine=False):
    return {"id": p.id, "name": p.name, "gender": p.gender, "father": p.father_id, "mother": p.mother_id, "spouse": p.spouse_id,
            "alive": p.alive, "born": p.born.isoformat() if p.born else "", "died": p.died.isoformat() if p.died else "",
            "married": p.married.isoformat() if p.married else "", "phone": p.phone, "city": p.city, "work": p.work, "notes": p.notes,
            "photo": _media(p.photo), "user": p.user_id, "username": (p.user.username or "") if p.user_id and p.user else "",
            "added_by": p.added_by_id}


def _can_edit(m, p, u):
    return _admin(m) or p.added_by_id == u.id or p.user_id == u.id or (m and m.person_id == p.id)


def _family_out(f, m):
    return {"id": f.id, "name": f.name, "clan": f.clan, "city": f.city, "country": f.country, "about": f.about,
            "code": f.code, "join_open": f.join_open, "created_by": f.created_by_id, "created_at": f.created_at.isoformat(),
            "role": m.role if m else "", "me": m.person_id if m else None}


def _save_pic(f, folder, size, square=False):
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); im.load()
    except Exception:
        return None
    im = ImageOps.exif_transpose(im).convert("RGB")
    if square:
        im = ImageOps.fit(im, (size, size), Image.LANCZOS)
    else:
        im.thumbnail((size, size), Image.LANCZOS)
    rel = os.path.join("roots", folder, timezone.localdate().strftime("%Y%m"), secrets.token_hex(10) + ".webp")
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=82)
    return rel


def _drop_pic(rel):
    if rel and rel.startswith("roots/"):
        try:
            os.remove(os.path.join(str(settings.MEDIA_ROOT), rel))
        except OSError:
            pass


def _ancestors(p):
    """ids of all ancestors of p (to stop loops like 'my son is my father')."""
    seen, todo = set(), [p.father_id, p.mother_id]
    rows = {x["id"]: x for x in Person.objects.filter(family_id=p.family_id).values("id", "father_id", "mother_id")}
    while todo:
        i = todo.pop()
        if i and i not in seen:
            seen.add(i)
            r = rows.get(i)
            if r:
                todo += [r["father_id"], r["mother_id"]]
    return seen


def _set_parent(child, field, parent):
    """father / mother of child. Returns an error text or ''."""
    if parent is None:
        setattr(child, field, None)
        return ""
    if parent.family_id != child.family_id or parent.id == child.id:
        return "That person is not in this family."
    if field == "father" and parent.gender != "m":
        return "A father must be a man."
    if field == "mother" and parent.gender != "f":
        return "A mother must be a woman."
    if child.id:
        # the parent must not be the child itself or one of the child's descendants
        kids = {child.id}; grow = True
        rows = list(Person.objects.filter(family_id=child.family_id).values("id", "father_id", "mother_id"))
        while grow:
            grow = False
            for r in rows:
                if r["id"] not in kids and (r["father_id"] in kids or r["mother_id"] in kids):
                    kids.add(r["id"]); grow = True
        if parent.id in kids:
            return "That would make a loop in the tree (a child cannot be a parent of their own parent)."
    setattr(child, field, parent)
    return ""


def _set_spouse(a, b):
    """Link a and b as husband and wife (both sides). b None = clear."""
    old = a.spouse
    if b is None:
        a.spouse = None; a.save(update_fields=["spouse", "updated_at"])
        if old and old.spouse_id == a.id:
            old.spouse = None; old.save(update_fields=["spouse", "updated_at"])
        return ""
    if b.family_id != a.family_id or b.id == a.id:
        return "That person is not in this family."
    if b.gender == a.gender:
        return "Husband and wife must be a man and a woman."
    if b.id in _ancestors(a) or a.id in _ancestors(b):
        return "A parent cannot be a spouse."
    if old and old.id != b.id and old.spouse_id == a.id:
        old.spouse = None; old.save(update_fields=["spouse", "updated_at"])
    if b.spouse_id and b.spouse_id != a.id:
        o = b.spouse
        if o and o.spouse_id == b.id:
            o.spouse = None; o.save(update_fields=["spouse", "updated_at"])
    a.spouse = b; b.spouse = a
    a.save(update_fields=["spouse", "updated_at"]); b.save(update_fields=["spouse", "updated_at"])
    return ""


def _fill(p, d, new=False):
    """Copy the editable fields from request data d into p. Returns an error text or ''."""
    if new or "name" in d:
        n = _txt(d.get("name"), 80)
        if len(n) < 2:
            return "Write the name."
        p.name = n
    if new or "gender" in d:
        g = str(d.get("gender") or "")[:1].lower()
        if g not in ("m", "f"):
            return "Choose male or female."
        if not new and g != p.gender and (p.spouse_id or Person.objects.filter(family_id=p.family_id).filter(
                **({"father": p} if p.gender == "m" else {"mother": p})).exists()):
            return "This person is already a parent or spouse in the tree, so male / female cannot change."
        p.gender = g
    for k in ("born", "died", "married"):
        if k in d:
            v = _day(d.get(k))
            if v is False:
                return "The %s date is not right." % {"born": "birth", "died": "death", "married": "marriage"}[k]
            setattr(p, k, v)
    if "alive" in d:
        p.alive = bool(d.get("alive")) and d.get("alive") not in ("0", "false", "no")
    if p.died:
        p.alive = False
    if p.born and p.died and p.died < p.born:
        return "Death date is before the birth date."
    if "phone" in d:
        p.phone = _phone(d.get("phone"))
    for k, n in (("city", 60), ("work", 80)):
        if k in d:
            setattr(p, k, _txt(d.get(k), n))
    if "notes" in d:
        p.notes = _long(d.get("notes"), 600)
    return ""


# ---------- list, create
@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    u = request.user
    out = {"signed": u.is_authenticated, "families": [], "pending": [], "staff": _staff(u), "links": LINKS, "kinds": Notice.KINDS}
    if not u.is_authenticated:
        return Response(out)
    out["name"] = _name(u)
    ms = Membership.objects.filter(user=u).select_related("family", "person").order_by("-created_at")
    counts = dict(Person.objects.filter(family__in=[m.family_id for m in ms]).values_list("family").annotate(n=Count("id")))
    for m in ms:
        row = {"id": m.family_id, "name": m.family.name, "clan": m.family.clan, "city": m.family.city, "role": m.role,
               "people": counts.get(m.family_id, 0), "me": m.person.name if m.person else ""}
        (out["pending"] if m.role == Membership.PENDING else out["families"]).append(row)
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create(request):
    u, d = request.user, request.data
    if Family.objects.filter(created_by=u).count() >= MAX_FAMILIES:
        return _err("You have started %d families already." % MAX_FAMILIES)
    name = _txt(d.get("name"), 80)
    if len(name) < 3:
        return _err("Write the family name (for example: Shah family of Multan).")
    me = d.get("me") if isinstance(d.get("me"), dict) else {}
    with transaction.atomic():
        f = Family.objects.create(name=name, code=_code(), clan=_txt(d.get("clan"), 60), city=_txt(d.get("city"), 60),
                                  country=_txt(d.get("country"), 40) or "Pakistan", about=_long(d.get("about"), 1000), created_by=u)
        p = Person(family=f, user=u, added_by=u)
        e = _fill(p, {"name": me.get("name") or _name(u), "gender": me.get("gender"), "born": me.get("born"),
                      "city": me.get("city") or f.city, "phone": me.get("phone") or getattr(u, "phone", "")}, new=True)
        if e:
            transaction.set_rollback(True)
            return _err(e)
        p.save()
        Membership.objects.create(family=f, user=u, role=Membership.ADMIN, person=p)
    return Response({"id": f.id, "code": f.code})


# ---------- one family
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def family(request, fid):
    u = request.user
    m = _mem(fid, u)
    if not m:
        return _err("This family is private. Ask a family member for an invite link or the family code.", 403)
    f = m.family
    if request.method == "GET":
        ppl = Person.objects.filter(family=f).select_related("user").order_by("id")
        out = _family_out(f, m)
        out["people"] = [_person(p) for p in ppl]
        out["can_edit"] = [p.id for p in ppl if _can_edit(m, p, u)]
        out["admin"] = _admin(m)
        out["members"] = Membership.objects.filter(family=f).exclude(role=Membership.PENDING).count()
        out["requests"] = Membership.objects.filter(family=f, role=Membership.PENDING).count() if _admin(m) else 0
        out["uid"] = u.id
        return Response(out)
    if request.method == "DELETE":
        if f.created_by_id != u.id and not (_admin(m) and not f.created_by_id):
            return _err("Only the person who started the family can delete it.", 403)
        if _txt(request.data.get("confirm"), 80).lower() != f.name.lower():
            return _err("Type the family name to confirm.")
        for ph in Photo.objects.filter(family=f):
            _drop_pic(ph.path)
        for p in Person.objects.filter(family=f).exclude(photo=""):
            _drop_pic(p.photo)
        f.delete()
        return Response({"ok": True})
    if not _admin(m):
        return _err("Only family admins can change this.", 403)
    d = request.data
    if "name" in d:
        n = _txt(d.get("name"), 80)
        if len(n) < 3:
            return _err("Write the family name.")
        f.name = n
    for k, n in (("clan", 60), ("city", 60), ("country", 40)):
        if k in d:
            setattr(f, k, _txt(d.get(k), n))
    if "about" in d:
        f.about = _long(d.get("about"), 1000)
    if "join_open" in d:
        f.join_open = bool(d.get("join_open"))
    if d.get("new_code"):
        f.code = _code()
    f.save()
    return Response(_family_out(f, m))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_person(request, fid):
    u, d = request.user, request.data
    m = _mem(fid, u)
    if not m:
        return _err("Only family members can add people.", 403)
    if Person.objects.filter(family_id=fid).count() >= MAX_PEOPLE:
        return _err("This family has %d people, the most a family can have." % MAX_PEOPLE)
    rel, to = str(d.get("rel") or ""), None
    if rel:
        if rel not in LINKS:
            return _err("Unknown relation.")
        to = Person.objects.filter(family_id=fid, pk=_int(d.get("to"))).first()
        if not to:
            return _err("Choose who this person is related to.")
    p = Person(family_id=fid, added_by=u)
    e = _fill(p, dict(d.items()) if hasattr(d, "items") else {}, new=True)
    if e:
        return _err(e)
    if rel in ("father", "son", "brother") and p.gender != "m" or rel in ("mother", "daughter", "sister") and p.gender != "f":
        return _err("Male / female does not match the relation.")
    with transaction.atomic():
        for k in ("father", "mother"):
            if d.get(k):
                par = Person.objects.filter(family_id=fid, pk=_int(d.get(k))).first()
                e = _set_parent(p, k, par) if par else "Parent not found."
                if e:
                    transaction.set_rollback(True)
                    return _err(e)
        if rel in ("son", "daughter"):
            # child of `to` (and of to's spouse)
            e = _set_parent(p, "father" if to.gender == "m" else "mother", to)
            sp = to.spouse
            if not e and sp and sp.spouse_id == to.id:
                e = _set_parent(p, "father" if sp.gender == "m" else "mother", sp)
            if e:
                transaction.set_rollback(True)
                return _err(e)
        elif rel in ("brother", "sister"):
            if not to.father_id and not to.mother_id:
                transaction.set_rollback(True)
                return _err("Add %s's father or mother first, then add brothers and sisters." % to.name)
            p.father_id, p.mother_id = to.father_id, to.mother_id
        p.save()
        if rel in ("father", "mother"):
            if getattr(to, rel + "_id"):
                transaction.set_rollback(True)
                return _err("%s already has a %s in the tree." % (to.name, rel))
            e = _set_parent(to, rel, p)
            if e:
                transaction.set_rollback(True)
                return _err(e)
            to.save(update_fields=[rel, "updated_at"])
            # the other parent becomes the spouse
            other = to.mother if rel == "father" else to.father
            if other and not other.spouse_id:
                _set_spouse(p, other)
        elif rel == "spouse":
            e = _set_spouse(p, to)
            if e:
                transaction.set_rollback(True)
                return _err(e)
        if d.get("spouse") and rel != "spouse":
            sp = Person.objects.filter(family_id=fid, pk=_int(d.get("spouse"))).first()
            if sp:
                e = _set_spouse(p, sp)
                if e:
                    transaction.set_rollback(True)
                    return _err(e)
    p.refresh_from_db()
    return Response(_person(p))


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def person(request, pid):
    u = request.user
    p = Person.objects.filter(pk=pid).select_related("user").first()
    m = p and _mem(p.family_id, u)
    if not m:
        return _err("Not found.", 404)
    if not _can_edit(m, p, u):
        return _err("Only a family admin, the person who added them, or the person themself can change this.", 403)
    if request.method == "DELETE":
        if p.user_id and p.user_id != u.id and not _admin(m):
            return _err("This person has joined with their account. Only an admin can remove them.", 403)
        if Person.objects.filter(family_id=p.family_id, user__isnull=False).count() == 1 and p.user_id:
            return _err("You cannot remove the last person with an account.")
        _drop_pic(p.photo)
        Membership.objects.filter(person=p).update(person=None)
        Person.objects.filter(spouse=p).update(spouse=None)
        p.delete()
        return Response({"ok": True})
    d = request.data
    e = _fill(p, d)
    if e:
        return _err(e)
    for k in ("father", "mother"):
        if k in d:
            v = _int(d.get(k))
            par = Person.objects.filter(family_id=p.family_id, pk=v).first() if v else None
            if v and not par:
                return _err("Parent not found.")
            e = _set_parent(p, k, par)
            if e:
                return _err(e)
    p.save()
    if "spouse" in d:
        v = _int(d.get("spouse"))
        sp = Person.objects.filter(family_id=p.family_id, pk=v).first() if v else None
        if v and not sp:
            return _err("Spouse not found.")
        e = _set_spouse(p, sp)
        if e:
            return _err(e)
    p.refresh_from_db()
    return Response(_person(p))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def person_photo(request, pid):
    u = request.user
    p = Person.objects.filter(pk=pid).first()
    m = p and _mem(p.family_id, u)
    if not m or not _can_edit(m, p, u):
        return _err("You cannot change this picture.", 403)
    if request.data.get("remove"):
        _drop_pic(p.photo); p.photo = ""; p.save(update_fields=["photo", "updated_at"])
        return Response(_person(p))
    f = request.FILES.get("file")
    if not f:
        return _err("Choose a picture.")
    if f.size > MAX_PIC_MB * 1024 * 1024:
        return _err("The picture is over %d MB." % MAX_PIC_MB)
    rel = _save_pic(f, "people", 400, square=True)
    if not rel:
        return _err("That file is not a picture we can read.")
    _drop_pic(p.photo); p.photo = rel; p.save(update_fields=["photo", "updated_at"])
    return Response(_person(p))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def this_is_me(request, fid):
    """Pick the person in the tree that is you (or clear it)."""
    u = request.user
    m = _mem(fid, u)
    if not m:
        return _err("Not a member.", 403)
    pid = _int(request.data.get("person"))
    if not pid:
        Person.objects.filter(family_id=fid, user=u).update(user=None)
        m.person = None; m.save(update_fields=["person"])
        return Response({"me": None})
    p = Person.objects.filter(family_id=fid, pk=pid).first()
    if not p:
        return _err("Not found.", 404)
    if p.user_id and p.user_id != u.id:
        return _err("Someone else has already said this is them. Ask an admin if this is a mistake.")
    with transaction.atomic():
        Person.objects.filter(family_id=fid, user=u).exclude(pk=p.pk).update(user=None)
        p.user = u; p.save(update_fields=["user", "updated_at"])
        m.person = p; m.save(update_fields=["person"])
    return Response({"me": p.id})


# ---------- joining
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join(request):
    """Step 1 {code}: shows the family and the people nobody has claimed. Step 2 {code, confirm, person, note}: asks to join."""
    u, d = request.user, request.data
    code = re.sub(r"[^A-Z0-9]", "", str(d.get("code") or "").upper())[:10]
    f = Family.objects.filter(code=code).first() if len(code) >= 6 else None
    if not f or not f.join_open:
        return _err("No family has this code. Check it with the person who sent it.", 404)
    m = Membership.objects.filter(family=f, user=u).first()
    if m and m.role != Membership.PENDING:
        return Response({"id": f.id, "member": True})
    if not d.get("confirm"):
        free = Person.objects.filter(family=f, user__isnull=True).order_by("name").values("id", "name", "gender", "alive", "father__name")
        return Response({"family": {"id": f.id, "name": f.name, "clan": f.clan, "city": f.city, "people": Person.objects.filter(family=f).count()},
                         "free": [{"id": x["id"], "name": x["name"], "gender": x["gender"], "father": x["father__name"] or ""} for x in free if x["alive"]],
                         "pending": bool(m)})
    pid = _int(d.get("person"))
    p = Person.objects.filter(family=f, pk=pid, user__isnull=True).first() if pid else None
    note = _txt(d.get("note"), 200)
    if not p and len(note) < 5:
        return _err("Pick your name in the list, or write who you are (for example: Ahmed's son, from Lahore).")
    if m:
        m.person, m.note = p, note; m.save(update_fields=["person", "note"])
    else:
        Membership.objects.create(family=f, user=u, role=Membership.PENDING, person=p, note=note)
        for a in Membership.objects.filter(family=f, role=Membership.ADMIN).select_related("user"):
            _notify(a.user, "%s asked to join %s. Open the family to approve." % (_name(u), f.name), "/roots#f%d/settings" % f.id)
    return Response({"pending": True, "name": f.name})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def requests_list(request, fid):
    m = _mem(fid, request.user)
    if not _admin(m):
        return _err("Only admins.", 403)
    rows = Membership.objects.filter(family_id=fid).select_related("user", "person").order_by("role", "-created_at")
    out = []
    for r in rows:
        out.append({"id": r.id, "name": _name(r.user), "username": r.user.username or "", "avatar": _avatar(r.user), "role": r.role,
                    "person": r.person_id, "person_name": r.person.name if r.person else "", "note": r.note,
                    "when": r.created_at.isoformat(), "you": r.user_id == request.user.id})
    inv = Invite.objects.filter(family_id=fid, used_by__isnull=True, expires__gt=timezone.now()).select_related("person").order_by("-created_at")[:30]
    return Response({"members": out, "invites": [{"token": i.token, "person": i.person.name if i.person else "", "expires": i.expires.isoformat()} for i in inv]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def member_act(request, fid, mid, act):
    u = request.user
    m = _mem(fid, u)
    r = Membership.objects.filter(family_id=fid, pk=mid).select_related("family", "user", "person").first()
    if not r:
        return _err("Not found.", 404)
    if act == "leave":
        if r.user_id != u.id:
            return _err("Not you.", 403)
    elif not _admin(m):
        return _err("Only admins.", 403)
    f = r.family
    if act == "approve" and r.role == Membership.PENDING:
        if r.person_id:
            p = r.person
            if p.user_id and p.user_id != r.user_id:
                r.person = None
            else:
                p.user = r.user; p.save(update_fields=["user", "updated_at"])
        r.role = Membership.MEMBER; r.save(update_fields=["role", "person"])
        _notify(r.user, "You are now a member of %s on Roots of Love." % f.name, "/roots#f%d" % f.id)
    elif act == "decline" and r.role == Membership.PENDING:
        r.delete()
    elif act in ("admin", "member") and r.role != Membership.PENDING:
        if act == "member" and r.role == Membership.ADMIN and Membership.objects.filter(family=f, role=Membership.ADMIN).count() == 1:
            return _err("A family needs at least one admin.")
        r.role = act; r.save(update_fields=["role"])
        if act == "admin":
            _notify(r.user, "You are now an admin of %s." % f.name, "/roots#f%d" % f.id)
    elif act in ("remove", "leave"):
        if r.role == Membership.ADMIN and Membership.objects.filter(family=f, role=Membership.ADMIN).count() == 1 \
                and Membership.objects.filter(family=f).exclude(role=Membership.PENDING).count() > 1:
            return _err("Make someone else an admin first.")
        Person.objects.filter(family=f, user=r.user).update(user=None)
        r.delete()
    else:
        return _err("Unknown action.")
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave(request, fid):
    r = Membership.objects.filter(family_id=fid, user=request.user).first()
    if not r:
        return _err("Not a member.", 404)
    f = r.family
    others = Membership.objects.filter(family=f).exclude(role=Membership.PENDING).exclude(pk=r.pk)
    if r.role == Membership.ADMIN and others.exists() and not others.filter(role=Membership.ADMIN).exists():
        return _err("Make someone else an admin first.")
    if r.role != Membership.PENDING and not others.exists():
        return _err("You are the only member. Delete the family tree instead, or invite someone first.")
    Person.objects.filter(family=f, user=request.user).update(user=None)
    r.delete()
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite(request, fid):
    u = request.user
    m = _mem(fid, u)
    if not m:
        return _err("Not a member.", 403)
    pid = _int(request.data.get("person"))
    p = Person.objects.filter(family_id=fid, pk=pid).first() if pid else None
    if pid and not p:
        return _err("Not found.", 404)
    if p and p.user_id:
        return _err("%s has already joined." % p.name)
    i = Invite.objects.filter(family_id=fid, person=p, used_by__isnull=True, expires__gt=timezone.now() + timedelta(days=3)).first() if p else None
    if not i:
        i = Invite.objects.create(family_id=fid, person=p, by=u, token=secrets.token_urlsafe(12)[:16], expires=timezone.now() + timedelta(days=INVITE_DAYS))
    return Response({"token": i.token, "link": "https://xpertcreation.com/roots#invite=" + i.token, "expires": i.expires.isoformat(),
                     "family": m.family.name, "person": p.name if p else "", "phone": p.phone if p else ""})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def invite_open(request, token):
    i = Invite.objects.filter(token=str(token)[:24]).select_related("family", "person", "by").first()
    if not i or i.used_by_id or i.expires < timezone.now():
        return _err("This invite link has expired or was used. Ask for a new one.", 404)
    f = i.family
    if request.method == "GET":
        return Response({"family": f.name, "clan": f.clan, "city": f.city, "by": _name(i.by), "person": i.person.name if i.person else "",
                         "people": Person.objects.filter(family=f).count(), "signed": request.user.is_authenticated})
    u = request.user
    if not u.is_authenticated:
        return _err("Sign in first.", 401)
    with transaction.atomic():
        m = Membership.objects.filter(family=f, user=u).first()
        if not m:
            m = Membership.objects.create(family=f, user=u, role=Membership.MEMBER)
        elif m.role == Membership.PENDING:
            m.role = Membership.MEMBER
        p = i.person
        if p and (not p.user_id or p.user_id == u.id) and not Person.objects.filter(family=f, user=u).exclude(pk=p.pk).exists():
            p.user = u; p.save(update_fields=["user", "updated_at"]); m.person = p
        m.save()
        i.used_by = u; i.save(update_fields=["used_by"])
    if i.by_id and i.by_id != u.id:
        _notify(i.by, "%s joined %s with your invite." % (_name(u), f.name), "/roots#f%d" % f.id)
    return Response({"id": f.id})


# ---------- notice board, album
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def notices(request, fid):
    u = request.user
    m = _mem(fid, u)
    if not m:
        return _err("Not a member.", 403)
    if request.method == "POST":
        d = request.data
        text = _long(d.get("text"), 1500)
        kind = str(d.get("kind") or "news")
        if kind not in KINDS:
            kind = "news"
        if len(text) < 3:
            return _err("Write something.")
        day = _day(d.get("day"))
        if day is False:
            return _err("The date is not right.")
        if Notice.objects.filter(family_id=fid, by=u, created_at__gte=timezone.now() - timedelta(hours=1)).count() >= 10:
            return _err("Too many posts in one hour. Try later.")
        n = Notice.objects.create(family_id=fid, by=u, kind=kind, text=text, day=day)
        if d.get("tell"):
            for r in Membership.objects.filter(family_id=fid).exclude(role=Membership.PENDING).exclude(user=u).select_related("user")[:500]:
                _notify(r.user, "%s (%s): %s" % (m.family.name, KINDS[kind], text[:120]), "/roots#f%d/board" % fid)
    rows = Notice.objects.filter(family_id=fid).select_related("by").order_by("-created_at")[:100]
    return Response({"items": [{"id": n.id, "kind": n.kind, "text": n.text, "day": n.day.isoformat() if n.day else "", "by": _name(n.by),
                                "avatar": _avatar(n.by) if n.by else "", "when": n.created_at.isoformat(),
                                "mine": n.by_id == u.id or _admin(m)} for n in rows]})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def notice(request, nid):
    n = Notice.objects.filter(pk=nid).first()
    m = n and _mem(n.family_id, request.user)
    if not m or (n.by_id != request.user.id and not _admin(m)):
        return _err("Not allowed.", 403)
    n.delete()
    return Response({"ok": True})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def photos(request, fid):
    u = request.user
    m = _mem(fid, u)
    if not m:
        return _err("Not a member.", 403)
    if request.method == "POST":
        if Photo.objects.filter(family_id=fid).count() >= MAX_PHOTOS:
            return _err("The album is full (%d pictures)." % MAX_PHOTOS)
        f = request.FILES.get("file")
        if not f:
            return _err("Choose a picture.")
        if f.size > MAX_PIC_MB * 1024 * 1024:
            return _err("The picture is over %d MB." % MAX_PIC_MB)
        rel = _save_pic(f, "album", 1600)
        if not rel:
            return _err("That file is not a picture we can read.")
        y = _int(request.data.get("year"))
        Photo.objects.create(family_id=fid, by=u, path=rel, caption=_txt(request.data.get("caption"), 200),
                             year=y if y and 1850 <= y <= date.today().year else None)
    rows = Photo.objects.filter(family_id=fid).select_related("by").order_by("-created_at")[:MAX_PHOTOS]
    return Response({"items": [{"id": p.id, "url": _media(p.path), "caption": p.caption, "year": p.year, "by": _name(p.by),
                                "when": p.created_at.isoformat(), "mine": p.by_id == u.id or _admin(m)} for p in rows]})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def photo(request, phid):
    p = Photo.objects.filter(pk=phid).first()
    m = p and _mem(p.family_id, request.user)
    if not m or (p.by_id != request.user.id and not _admin(m)):
        return _err("Not allowed.", 403)
    if request.method == "POST":
        p.caption = _txt(request.data.get("caption"), 200)
        y = _int(request.data.get("year"))
        p.year = y if y and 1850 <= y <= date.today().year else None
        p.save(update_fields=["caption", "year"])
        return Response({"ok": True})
    _drop_pic(p.path); p.delete()
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export(request, fid):
    m = _mem(fid, request.user)
    if not m:
        return _err("Not a member.", 403)
    f = m.family
    data = {"app": "XpertCreation Roots of Love", "saved": timezone.now().isoformat(), "family": {k: v for k, v in _family_out(f, m).items() if k not in ("role", "me", "code")},
            "people": [_person(p) for p in Person.objects.filter(family=f).select_related("user").order_by("id")],
            "notices": [{"kind": n.kind, "text": n.text, "day": n.day.isoformat() if n.day else "", "when": n.created_at.isoformat()} for n in Notice.objects.filter(family=f)],
            "photos": [{"url": "https://xpertcreation.com" + _media(p.path), "caption": p.caption, "year": p.year} for p in Photo.objects.filter(family=f)]}
    r = HttpResponse(json.dumps(data, ensure_ascii=False, indent=1), content_type="application/json; charset=utf-8")
    r["Content-Disposition"] = 'attachment; filename="roots-%s-%s.json"' % (re.sub(r"[^a-z0-9]+", "-", f.name.lower()).strip("-")[:40] or "family", timezone.localdate().isoformat())
    return r


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    if not _staff(request.user):
        return _err("Team only.", 403)
    fams = Family.objects.annotate(n=Count("people", distinct=True), mm=Count("memberships", distinct=True)).select_related("created_by").order_by("-created_at")[:200]
    return Response({"families": Family.objects.count(), "people": Person.objects.count(), "members": Membership.objects.exclude(role=Membership.PENDING).count(),
                     "photos": Photo.objects.count(), "week": Family.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
                     "rows": [{"id": f.id, "name": f.name, "city": f.city, "people": f.n, "members": f.mm, "by": _name(f.created_by),
                               "when": f.created_at.isoformat()} for f in fams]})
