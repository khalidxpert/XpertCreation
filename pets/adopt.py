"""Free pet adoption and a directory of vets.

Adoption: an owner lists a pet; people send a request with a message; the owner accepts one and a chat
opens between them. Nobody pays anyone - selling pets is against the rules and gets removed.
Vets: members add clinics; a moderator approves them before they appear.
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from notifications.views import notify, notify_admins, open_thread

from .models import SPECIES, AdoptionPost, AdoptionRequest, VetClinic
from .views import BrowseThrottle, EditThrottle, LostThrottle, YES, _drop, _err, _long, _name, _phone, _save_photo, _txt, _url

SPECIES_KEYS = dict(SPECIES)
POSTS_PER_DAY = 5


def _mod(u):
    return bool(u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _place(d):
    cc = _txt(d.get("country"), 2).upper()
    return (cc if len(cc) == 2 and cc.isalpha() else ""), _txt(d.get("state"), 100), _txt(d.get("city"), 100)


def _post(x, u, full=False):
    out = {"id": x.id, "name": x.name, "species": x.species, "breed": x.breed, "gender": x.gender, "age": x.age_text,
           "vaccinated": x.vaccinated, "neutered": x.neutered, "photos": [_url(p) for p in x.photos or []],
           "country": x.country, "state": x.state, "city": x.city, "description": x.description, "status": x.status,
           "hidden": x.hidden, "when": x.created_at.strftime("%d %b %Y"), "owner_name": _name(x.owner).split()[0],
           "is_mine": u.is_authenticated and u.pk == x.owner_id, "can_moderate": _mod(u)}
    if u.is_authenticated and u.pk != x.owner_id:
        r = x.requests.filter(requester=u).first()
        out["my_request"] = r.status if r else None
    if full and out["is_mine"]:
        out["requests_waiting"] = x.requests.filter(status="pending").count()
    return out


def _fill(x, d):
    x.name = _txt(d.get("name"), 60) or x.name
    if d.get("species") in SPECIES_KEYS:
        x.species = d.get("species")
    for f, n in (("breed", 80), ("age_text", 40)):
        if f in d:
            setattr(x, f, _txt(d.get(f), n))
    if d.get("gender") in dict(AdoptionPost.GENDERS):
        x.gender = d.get("gender")
    for f in ("vaccinated", "neutered"):
        if f in d:
            setattr(x, f, d.get(f) in YES)
    if "description" in d:
        x.description = _long(d.get("description"), 2000)
    if "city" in d:
        x.country, x.state, x.city = _place(d)
    if not x.name:
        raise ValueError("Give the pet's name.")
    if len(x.description) < 20:
        raise ValueError("Tell people a little about the pet (at least 20 letters).")
    if not x.city:
        raise ValueError("Pick the city where the pet is.")
    low = x.description.lower()
    if any(w in low for w in ("price", "rs.", "rs ", "pkr", "rupees", "for sale", "sell")):
        raise ValueError("Adoption here is free. Please remove any price or mention of selling.")


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def adopt_list(request):
    u = request.user
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in to list a pet.", 401)
        if not getattr(u, "is_email_verified", True):
            return _err("Verify your email before listing a pet.", 403)
        if not LostThrottle().allow_request(request, None) or \
                AdoptionPost.objects.filter(owner=u, created_at__date=timezone.localdate()).count() >= POSTS_PER_DAY:
            return _err("You have listed a lot today. Try again tomorrow.", 429)
        x = AdoptionPost(owner=u)
        if request.data.get("pet_id"):
            from .models import Pet
            p = Pet.objects.filter(pk=request.data.get("pet_id"), owner=u).first()
            if p:
                x.pet, x.name, x.species, x.breed, x.gender = p, p.name, p.species, p.breed, p.gender
        try:
            _fill(x, request.data)
        except ValueError as e:
            return _err(str(e))
        x.save()
        return Response(_post(x, u, True), status=201)

    qs = AdoptionPost.objects.select_related("owner").filter(hidden=False, status__in=["available", "reserved"])
    g = request.GET
    if g.get("mine") in YES and u.is_authenticated:
        qs = AdoptionPost.objects.select_related("owner").filter(owner=u)
    if g.get("species") in SPECIES_KEYS:
        qs = qs.filter(species=g.get("species"))
    if g.get("city"):
        qs = qs.filter(city__iexact=_txt(g.get("city"), 100))
    elif g.get("country"):
        qs = qs.filter(country=_txt(g.get("country"), 2).upper())
    return Response({"posts": [_post(x, u) for x in qs[:100]]})


def _get(pk, u):
    x = AdoptionPost.objects.select_related("owner").filter(pk=pk).first()
    if not x or (x.hidden and not (_mod(u) or (u.is_authenticated and u.pk == x.owner_id))):
        return None
    return x


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def adopt_detail(request, pk):
    u = request.user
    x = _get(pk, u)
    if not x:
        return _err("This listing is not available.", 404)
    if request.method == "GET":
        return Response(_post(x, u, True))
    if not u.is_authenticated:
        return _err("Sign in first.", 401)
    if request.method == "DELETE":
        if u.pk != x.owner_id and not _mod(u):
            return _err("Not yours.", 403)
        for p in x.photos or []:
            _drop(p)
        x.delete()
        return Response({"deleted": True})
    d = request.data
    if "hidden" in d:
        if not _mod(u):
            return _err("Only moderators can hide listings.", 403)
        x.hidden = d.get("hidden") in YES
        x.save(update_fields=["hidden"])
        return Response(_post(x, u, True))
    if u.pk != x.owner_id:
        return _err("Not yours.", 403)
    if d.get("status") in dict(AdoptionPost.STATES) and len(d) == 1:
        x.status = d.get("status")
        x.save(update_fields=["status"])
        if x.status == "adopted":
            x.requests.filter(status="pending").update(status="declined")
        return Response(_post(x, u, True))
    try:
        _fill(x, d)
    except ValueError as e:
        return _err(str(e))
    x.save()
    return Response(_post(x, u, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([EditThrottle])
def adopt_photos(request, pk):
    x = AdoptionPost.objects.filter(pk=pk, owner=request.user).first()
    if not x:
        return _err("Listing not found.", 404)
    files = request.FILES.getlist("photos")
    if not files:
        return _err("Pick a photo.")
    photos = list(x.photos or [])
    for f in files[:4 - len(photos)]:
        try:
            photos.append(_save_photo(f, "adopt%d" % x.id))
        except ValueError as e:
            x.photos = photos
            x.save(update_fields=["photos"])
            return _err(str(e))
    x.photos = photos
    x.save(update_fields=["photos"])
    return Response(_post(x, request.user, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def adopt_request(request, pk):
    u = request.user
    x = _get(pk, u)
    if not x or x.status != "available":
        return _err("This pet is not taking requests now.", 404)
    if x.owner_id == u.pk:
        return _err("This is your own listing.")
    msg = _long(request.data.get("message"), 1000)
    if len(msg) < 20:
        return _err("Tell the owner about your home and why you would like to adopt (at least 20 letters).")
    r, made = AdoptionRequest.objects.get_or_create(post=x, requester=u, defaults={"message": msg})
    if not made:
        if r.status not in ("withdrawn", "declined"):
            return _err("You have already asked.")
        r.status, r.message = "pending", msg
        r.save(update_fields=["status", "message"])
    notify(x.owner, "pet", "%s would like to adopt %s." % (_name(u), x.name), "/adopt/%d" % x.id)
    return Response({"status": "pending"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def adopt_requests(request, pk):
    x = AdoptionPost.objects.filter(pk=pk, owner=request.user).first()
    if not x:
        return _err("Listing not found.", 404)
    from network.models import ProProfile
    out = []
    for r in x.requests.exclude(status="withdrawn").select_related("requester"):
        p = ProProfile.objects.filter(user=r.requester).first()
        out.append({"id": r.id, "name": _name(r.requester), "slug": p.slug if p else None, "city": getattr(p, "city", "") if p else "",
                    "message": r.message, "status": r.status, "when": r.created_at.strftime("%d %b")})
    return Response({"requests": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def adopt_answer(request, rid, action):
    r = AdoptionRequest.objects.select_related("post", "requester").filter(pk=rid, post__owner=request.user).first()
    if not r or action not in ("accept", "decline"):
        return _err("Not found.", 404)
    if r.status in ("withdrawn",):
        return _err("That request was withdrawn.")
    chat = None
    if action == "accept":
        r.status = "accepted"
        r.save(update_fields=["status"])
        if r.post.status == "available":
            r.post.status = "reserved"
            r.post.save(update_fields=["status"])
        chat = open_thread("adopt", r.id, request.user, r.requester).id
        notify(r.requester, "pet", "Good news: %s accepted your request for %s. You can chat now." % (_name(request.user), r.post.name), "/chat/%d" % chat)
    else:
        r.status = "declined"
        r.save(update_fields=["status"])
        notify(r.requester, "pet", "Your request for %s was not accepted this time." % r.post.name, "/adopt")
    return Response({"status": r.status, "chat": chat})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def adopt_my_requests(request):
    rows = AdoptionRequest.objects.filter(requester=request.user).select_related("post", "post__owner")[:100]
    return Response({"requests": [{"id": r.id, "status": r.status, "post": _post(r.post, request.user)} for r in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def adopt_withdraw(request, pk):
    n = AdoptionRequest.objects.filter(post_id=pk, requester=request.user, status="pending").update(status="withdrawn")
    return Response({"withdrawn": n})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def adopt_report(request, pk):
    x = _get(pk, request.user)
    if not x:
        return _err("Not found.", 404)
    why = _txt(request.data.get("reason"), 40) or "other"
    notify_admins("report", "Adoption listing reported (%s): %s in %s" % (why, x.name, x.city), "/admin/pets/adoptionpost/%d/change/" % x.id)
    return Response({"ok": True})


# ---------------------------------------------------------------- vets

def _vet(v, u):
    return {"id": v.id, "name": v.name, "country": v.country, "state": v.state, "city": v.city, "address": v.address,
            "phone": v.phone, "hours": v.hours, "services": v.services, "emergency": v.emergency, "map_url": v.map_url,
            "approved": v.approved, "can_moderate": _mod(u)}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def vets(request):
    u = request.user
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in to add a vet.", 401)
        if not LostThrottle().allow_request(request, None):
            return _err("You have added a lot today. Try again tomorrow.", 429)
        d = request.data
        cc, st, city = _place(d)
        name = _txt(d.get("name"), 120)
        if not name or not city:
            return _err("Add the clinic's name and city.")
        mu = _txt(d.get("map_url"), 300)
        if mu and not mu.startswith("https://"):
            mu = ""
        v = VetClinic.objects.create(added_by=u, name=name, country=cc, state=st, city=city, address=_txt(d.get("address"), 250),
                                     phone=_phone(d.get("phone")), hours=_txt(d.get("hours"), 120), services=_txt(d.get("services"), 300),
                                     emergency=d.get("emergency") in YES, map_url=mu, approved=_mod(u))
        if not v.approved:
            notify_admins("pet", "New vet to check: %s, %s" % (v.name, v.city), "/vets?review=1")
        return Response(_vet(v, u), status=201)
    qs = VetClinic.objects.all() if (request.GET.get("review") in YES and _mod(u)) else VetClinic.objects.filter(approved=True)
    if request.GET.get("review") in YES and _mod(u):
        qs = qs.filter(approved=False)
    if request.GET.get("city"):
        qs = qs.filter(city__iexact=_txt(request.GET.get("city"), 100))
    elif request.GET.get("country"):
        qs = qs.filter(country=_txt(request.GET.get("country"), 2).upper())
    if request.GET.get("emergency") in YES:
        qs = qs.filter(emergency=True)
    return Response({"vets": [_vet(v, u) for v in qs[:200]]})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def vet_moderate(request, pk):
    if not _mod(request.user):
        return _err("Only moderators can do that.", 403)
    v = VetClinic.objects.filter(pk=pk).first()
    if not v:
        return _err("Not found.", 404)
    if request.method == "DELETE":
        v.delete()
        return Response({"deleted": True})
    v.approved = request.data.get("approved") in YES
    v.save(update_fields=["approved"])
    return Response(_vet(v, request.user))
