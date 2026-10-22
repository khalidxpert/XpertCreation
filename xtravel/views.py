import os
import re
import secrets
from datetime import date, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Block, Booking, Property, Review, Room, Tour

HELD = ("pending", "confirmed", "checked_in")     # these hold a room / a seat
AMENITIES = ["wifi", "parking", "breakfast", "ac", "heating", "hot_water", "tv", "restaurant", "room_service", "family", "prayer_room",
             "generator", "pool", "gym", "airport_pickup", "laundry", "mountain_view", "lake_view", "pets", "wheelchair"]
INCLUDES = ["hotel", "transport", "meals", "breakfast", "guide", "tickets", "jeep", "flights", "visa", "insurance", "photos", "bonfire"]
MAX_PHOTOS = 12


def _err(m, c=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": m}, status=c)


def _t(v, n):
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(v or "")).strip()[:n]


def _int(v, lo, hi, d=0):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return d


def _date(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _media(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p and not p.startswith(("http", "/")) else (p or "")


def _is_mod(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _name(u):
    return (getattr(u, "full_name", "") or "").strip() or u.get_username()


def _notify(u, text, link):
    try:
        from notifications.views import notify
        notify(u, "travel", text, link)
    except Exception:
        pass


def _slow(u, what, secs):
    k = "xtravel:%s:%s" % (what, u.pk)
    if cache.get(k):
        return True
    cache.set(k, 1, secs)
    return False


def _slug(model, base, me=None):
    b = slugify(base)[:70] or "place"
    s, i = b, 2
    while model.objects.filter(slug=s).exclude(pk=me).exists():
        s = "%s-%d" % (b, i); i += 1
    return s


def _companies(u):
    from companies.models import Company
    return Company.objects.filter(owner=u, status=Company.APPROVED)


def _clean_list(v, allowed=None, n=30, ln=60):
    out = []
    for x in (v if isinstance(v, list) else []):
        x = _t(x, ln)
        if x and (allowed is None or x in allowed) and x not in out:
            out.append(x)
    return out[:n]


# ---------------------------------------------------------------- availability
def nights(a, b):
    return [a + timedelta(days=i) for i in range((b - a).days)]


def free_rooms(room, a, b, skip=None):
    """How many rooms of this type are free on every night from a to b (b = check-out)."""
    if not a or not b or b <= a:
        return room.count
    bk = list(room.bookings.filter(status__in=HELD, start__lt=b, end__gt=a).exclude(pk=skip).values_list("start", "end", "qty"))
    bl = list(room.blocks.filter(start__lt=b, end__gt=a).values_list("start", "end", "count"))
    low = room.count
    for n in nights(a, b):
        used = sum(q for s, e, q in bk if s <= n < e) + sum(q for s, e, q in bl if s <= n < e)
        low = min(low, room.count - used)
    return max(0, low)


def seats_left(tour, d, skip=None):
    taken = tour.bookings.filter(status__in=HELD, start=d).exclude(pk=skip).aggregate(a=Sum("qty"), c=Sum("children"))
    used = (taken["a"] or 0) + (taken["c"] or 0)
    for dep in tour.departures or []:
        if dep.get("d") == d.isoformat():
            return max(0, int(dep.get("seats") or 0) - used)
    return None if tour.departures else max(0, tour.max_group * 3 - used)    # on request: a soft cap per day


# ---------------------------------------------------------------- shapes
def _company(c):
    return {"id": c.id, "name": c.name, "slug": c.slug, "verified": c.status == "approved", "logo": _media(getattr(c, "logo", ""))}


def shape_room(r, a=None, b=None):
    d = {"id": r.id, "name": r.name, "adults": r.adults, "beds": r.beds, "price": r.price, "count": r.count, "about": r.about,
         "amenities": r.amenities, "photos": [_media(p) for p in r.photos], "raw_photos": r.photos, "active": r.active}
    if a and b:
        d["free"] = free_rooms(r, a, b); d["nights"] = (b - a).days; d["total"] = r.price * d["nights"]
    return d


def shape_prop(p, full=False, a=None, b=None, mine=False):
    rooms = [r for r in p.rooms.all() if r.active or mine]
    prices = [r.price for r in rooms if r.active]
    d = {"id": p.id, "slug": p.slug, "name": p.name, "kind": p.kind, "kind_label": dict(Property.KINDS).get(p.kind, ""), "stars": p.stars,
         "city": p.city, "area": p.area, "country": p.country, "photo": _media(p.photos[0]) if p.photos else "", "from": min(prices) if prices else 0,
         "rating": round(p.rating, 1), "reviews": p.reviews, "featured": p.featured, "amenities": p.amenities[:8], "url": "/hotels?h=" + p.slug,
         "company": _company(p.company)}
    if a and b:
        d["available"] = any(free_rooms(r, a, b) > 0 for r in rooms if r.active)
    if full or mine:
        d.update({"about": p.about, "address": p.address, "map_url": p.map_url, "photos": [_media(x) for x in p.photos], "amenities": p.amenities,
                  "check_in": p.check_in, "check_out": p.check_out, "policies": p.policies, "rooms": [shape_room(r, a, b) for r in rooms],
                  "phone": p.phone, "whatsapp": p.whatsapp})
    if mine:
        d.update({"status": p.status, "status_label": dict(Property._meta.get_field("status").choices).get(p.status), "review_note": p.review_note,
                  "company_id": p.company_id, "raw_photos": p.photos})
    return d


def shape_tour(t, full=False, mine=False):
    deps = []
    today = timezone.localdate()
    for dep in sorted(t.departures or [], key=lambda x: x.get("d", "")):
        dd = _date(dep.get("d"))
        if dd and (dd >= today or mine):
            deps.append({"d": dep["d"], "seats": dep.get("seats", 0), "left": seats_left(t, dd)})
    d = {"id": t.id, "slug": t.slug, "title": t.title, "destination": t.destination, "start_city": t.start_city, "country": t.country,
         "days": t.days, "nights": t.nights, "price": t.price, "child_price": t.child_price, "photo": _media(t.photos[0]) if t.photos else "",
         "includes": t.includes, "rating": round(t.rating, 1), "reviews": t.reviews, "featured": t.featured, "url": "/tours?t=" + t.slug,
         "next": deps[0]["d"] if deps else None, "on_request": not t.departures, "company": _company(t.company)}
    if full or mine:
        d.update({"about": t.about, "excludes": t.excludes, "itinerary": t.itinerary, "departures": deps, "photos": [_media(x) for x in t.photos],
                  "max_group": t.max_group, "phone": t.phone, "whatsapp": t.whatsapp})
    if mine:
        d.update({"status": t.status, "review_note": t.review_note, "company_id": t.company_id, "raw_photos": t.photos})
    return d


def shape_booking(b, side="guest"):
    d = {"id": b.id, "code": b.code, "kind": b.kind, "status": b.status, "status_label": dict(Booking.STATUS).get(b.status), "name": b.name,
         "start": b.start.isoformat(), "end": b.end.isoformat() if b.end else None, "qty": b.qty, "children": b.children, "guests": b.guests,
         "total": b.total, "note": b.note, "owner_note": b.owner_note, "created": b.created_at.isoformat(),
         "nights": (b.end - b.start).days if b.end else 0, "reviewed": hasattr(b, "review")}
    if b.kind == "room":
        p = b.room.prop
        d.update({"room": b.room.name, "price": b.room.price, "place": p.name, "place_url": "/hotels?h=" + p.slug, "city": p.city, "address": p.address,
                  "check_in": p.check_in, "check_out": p.check_out, "company": p.company.name})
        contact = {"phone": p.phone, "whatsapp": p.whatsapp}
    else:
        t = b.tour
        d.update({"place": t.title, "place_url": "/tours?t=" + t.slug, "city": t.destination, "price": t.price, "child_price": t.child_price,
                  "days": t.days, "company": t.company.name})
        contact = {"phone": t.phone, "whatsapp": t.whatsapp}
    if side == "owner":
        d["phone"] = b.phone
    if side == "guest" and b.status in ("pending", "confirmed", "checked_in", "done"):
        d["contact"] = contact
    return d


# ---------------------------------------------------------------- public
def _approved_props():
    return Property.objects.filter(status="approved").select_related("company").prefetch_related("rooms")


@api_view(["GET"])
@permission_classes([AllowAny])
def hotels(request):
    q = _t(request.GET.get("q"), 60)
    a, b = _date(request.GET.get("in")), _date(request.GET.get("out"))
    if a and b and (b <= a or (b - a).days > 30):
        a = b = None
    guests = _int(request.GET.get("guests"), 1, 30, 1)
    qs = _approved_props()
    if q:
        qs = qs.filter(Q(city__icontains=q) | Q(area__icontains=q) | Q(name__icontains=q))
    kind = request.GET.get("kind")
    if kind in dict(Property.KINDS):
        qs = qs.filter(kind=kind)
    out = []
    for p in qs.order_by("-featured", "-rating", "-id")[:120]:
        s = shape_prop(p, a=a, b=b)
        if not s["from"]:
            continue
        if any(r.adults * r.count >= guests for r in p.rooms.all() if r.active):
            out.append(s)
    if a and b:
        out.sort(key=lambda x: (not x.get("available"), not x["featured"]))
    sort = request.GET.get("sort")
    if sort == "price":
        out.sort(key=lambda x: x["from"])
    cities = list(Property.objects.filter(status="approved").values("city").annotate(n=Count("id")).order_by("-n")[:30])
    return Response({"hotels": out[:60], "cities": cities})


@api_view(["GET"])
@permission_classes([AllowAny])
def hotel(request, slug):
    p = _approved_props().filter(slug=slug[:90]).first()
    mine = False
    if not p and request.user.is_authenticated:
        p = Property.objects.filter(slug=slug[:90]).select_related("company").prefetch_related("rooms").first()
        if p and not (p.owner_id == request.user.pk or _is_mod(request.user)):
            p = None
        mine = bool(p)
    if not p:
        return _err("This place was not found.", 404)
    a, b = _date(request.GET.get("in")), _date(request.GET.get("out"))
    if a and b and (b <= a or (b - a).days > 30):
        a = b = None
    d = shape_prop(p, full=True, a=a, b=b)
    d["preview"] = mine and p.status != "approved"
    d["review_list"] = [{"stars": r.stars, "text": r.text, "name": r.booking.name.split(" ")[0], "when": r.created_at.strftime("%b %Y")}
                        for r in Review.objects.filter(booking__room__prop=p).select_related("booking").order_by("-id")[:20]]
    return Response(d)


@api_view(["GET"])
@permission_classes([AllowAny])
def tours(request):
    q = _t(request.GET.get("q"), 60)
    qs = Tour.objects.filter(status="approved").select_related("company")
    if q:
        qs = qs.filter(Q(destination__icontains=q) | Q(title__icontains=q) | Q(start_city__icontains=q))
    out = [shape_tour(t) for t in qs.order_by("-featured", "-rating", "-id")[:80]]
    if request.GET.get("sort") == "price":
        out.sort(key=lambda x: x["price"])
    dests = list(Tour.objects.filter(status="approved").values("destination").annotate(n=Count("id")).order_by("-n")[:30])
    return Response({"tours": out, "destinations": dests})


@api_view(["GET"])
@permission_classes([AllowAny])
def tour(request, slug):
    t = Tour.objects.filter(slug=slug[:90]).select_related("company").first()
    if not t or (t.status != "approved" and not (request.user.is_authenticated and (t.owner_id == request.user.pk or _is_mod(request.user)))):
        return _err("This tour was not found.", 404)
    d = shape_tour(t, full=True)
    d["preview"] = t.status != "approved"
    d["review_list"] = [{"stars": r.stars, "text": r.text, "name": r.booking.name.split(" ")[0], "when": r.created_at.strftime("%b %Y")}
                        for r in Review.objects.filter(booking__tour=t).select_related("booking").order_by("-id")[:20]]
    return Response(d)


# ---------------------------------------------------------------- guests: book, my trips, cancel, review
def _code():
    while True:
        c = "XC" + secrets.token_hex(3).upper()
        if not Booking.objects.filter(code=c).exists():
            return c


def _guest_fields(request):
    name = _t(request.data.get("name"), 80) or _name(request.user)
    phone = re.sub(r"[^\d+ ]", "", str(request.data.get("phone") or ""))[:30].strip()
    if len(re.sub(r"\D", "", phone)) < 7:
        return None, None, "Enter a phone number the hotel can call."
    return name, phone, None


def _too_many(u):
    return Booking.objects.filter(guest=u, status="pending", created_at__gte=timezone.now() - timedelta(hours=24)).count() >= 8


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_room(request):
    u = request.user
    if _slow(u, "book", 4):
        return _err("One moment, please.", 429)
    if _too_many(u):
        return _err("You have many bookings waiting. Wait for the owners to answer, or cancel some first.")
    room = Room.objects.filter(pk=_int(request.data.get("room"), 0, 10 ** 9), active=True, prop__status="approved").select_related("prop", "prop__owner").first()
    if not room:
        return _err("This room is not available.")
    a, b = _date(request.data.get("in")), _date(request.data.get("out"))
    today = timezone.localdate()
    if not a or not b or a < today or b <= a:
        return _err("Pick your check-in and check-out dates.")
    if (b - a).days > 30:
        return _err("You can book up to 30 nights at a time.")
    if a > today + timedelta(days=400):
        return _err("Bookings open up to a year ahead.")
    qty = _int(request.data.get("rooms"), 1, 20, 1)
    guests = _int(request.data.get("guests"), 1, 60, 1)
    if guests > room.adults * qty + qty:            # one extra child per room is fine
        return _err("%d guests do not fit in %d room%s of this type (up to %d adults each). Book more rooms." % (guests, qty, "" if qty == 1 else "s", room.adults))
    name, phone, bad = _guest_fields(request)
    if bad:
        return _err(bad)
    if room.prop.owner_id == u.pk:
        return _err("This is your own place - add the booking in Manage instead (block the rooms).")
    with transaction.atomic():
        Room.objects.select_for_update().filter(pk=room.pk).first()
        left = free_rooms(room, a, b)
        if left < qty:
            return _err("Only %d room%s of this type %s free on those dates." % (left, "" if left == 1 else "s", "is" if left == 1 else "are") if left else "This room is fully booked on those dates. Try other dates or another room.")
        bk = Booking.objects.create(code=_code(), kind="room", room=room, guest=u, name=name, phone=phone, start=a, end=b, qty=qty, guests=guests,
                                    total=room.price * qty * (b - a).days, note=_t(request.data.get("note"), 300))
    _notify(room.prop.owner, "\U0001F3E8 New booking request %s: %s, %s, %s to %s" % (bk.code, name, room.name, a.strftime("%d %b"), b.strftime("%d %b")), "/travel-manage#b%d" % bk.id)
    return Response(shape_booking(bk), status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_tour(request, slug):
    u = request.user
    if _slow(u, "book", 4):
        return _err("One moment, please.", 429)
    if _too_many(u):
        return _err("You have many bookings waiting. Wait for the owners to answer, or cancel some first.")
    t = Tour.objects.filter(slug=slug[:90], status="approved").select_related("owner").first()
    if not t:
        return _err("This tour is not available.")
    d = _date(request.data.get("date"))
    today = timezone.localdate()
    if not d or d <= today:
        return _err("Pick a travel date.")
    if t.departures and d.isoformat() not in [x.get("d") for x in t.departures]:
        return _err("Pick one of the departure dates.")
    adults = _int(request.data.get("adults"), 1, 60, 1)
    kids = _int(request.data.get("children"), 0, 30, 0)
    if adults + kids > t.max_group:
        return _err("This tour takes up to %d people per booking." % t.max_group)
    name, phone, bad = _guest_fields(request)
    if bad:
        return _err(bad)
    if t.owner_id == u.pk:
        return _err("This is your own tour.")
    with transaction.atomic():
        Tour.objects.select_for_update().filter(pk=t.pk).first()
        left = seats_left(t, d)
        if left is not None and left < adults + kids:
            return _err("Only %d seat%s left on that date." % (left, "" if left == 1 else "s") if left else "This date is full. Pick another date.")
        bk = Booking.objects.create(code=_code(), kind="tour", tour=t, guest=u, name=name, phone=phone, start=d, qty=adults, children=kids, guests=adults + kids,
                                    total=t.price * adults + (t.child_price or t.price) * kids, note=_t(request.data.get("note"), 300))
    _notify(t.owner, "\U0001F9F3 New tour booking %s: %s, %d people, %s" % (bk.code, name, adults + kids, d.strftime("%d %b")), "/travel-manage#b%d" % bk.id)
    return Response(shape_booking(bk), status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_trips(request):
    qs = Booking.objects.filter(guest=request.user).select_related("room__prop__company", "tour__company")[:100]
    return Response({"bookings": [shape_booking(b) for b in qs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def my_cancel(request, pk):
    b = Booking.objects.filter(pk=pk, guest=request.user).select_related("room__prop__owner", "tour__owner").first()
    if not b:
        return _err("Booking not found.", 404)
    if b.status not in ("pending", "confirmed") or b.start < timezone.localdate():
        return _err("This booking can no longer be cancelled here. Call the owner.")
    b.status = "cancelled"; b.save(update_fields=["status", "updated_at"])
    owner = b.room.prop.owner if b.kind == "room" else b.tour.owner
    _notify(owner, "Booking %s was cancelled by the guest (%s)." % (b.code, b.name), "/travel-manage#b%d" % b.id)
    return Response(shape_booking(b))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def my_review(request, pk):
    b = Booking.objects.filter(pk=pk, guest=request.user, status="done").select_related("room__prop", "tour").first()
    if not b:
        return _err("You can review after your stay or tour is completed.")
    if hasattr(b, "review"):
        return _err("You already reviewed this.")
    stars = _int(request.data.get("stars"), 1, 5, 0)
    if not stars:
        return _err("Pick 1 to 5 stars.")
    Review.objects.create(booking=b, stars=stars, text=_t(request.data.get("text"), 600))
    if b.kind == "room":
        p = b.room.prop
        agg = Review.objects.filter(booking__room__prop=p).aggregate(a=Avg("stars"), n=Count("id"))
        Property.objects.filter(pk=p.pk).update(rating=agg["a"] or 0, reviews=agg["n"])
    else:
        agg = Review.objects.filter(booking__tour=b.tour).aggregate(a=Avg("stars"), n=Count("id"))
        Tour.objects.filter(pk=b.tour_id).update(rating=agg["a"] or 0, reviews=agg["n"])
    return Response({"ok": True})


# ---------------------------------------------------------------- owners
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def manage(request):
    u = request.user
    props = Property.objects.filter(owner=u).select_related("company").prefetch_related("rooms")
    trs = Tour.objects.filter(owner=u).select_related("company")
    bk = Booking.objects.filter(Q(room__prop__owner=u) | Q(tour__owner=u)).select_related("room__prop__company", "tour__company")
    st = request.GET.get("status")
    if st in dict(Booking.STATUS):
        bk = bk.filter(status=st)
    elif st == "upcoming":
        bk = bk.filter(status__in=("pending", "confirmed", "checked_in"))
    try:
        comps = [_company(c) for c in _companies(u)]
    except Exception:
        comps = []
    out = {"companies": comps, "properties": [shape_prop(p, mine=True) for p in props], "tours": [shape_tour(t, mine=True) for t in trs],
           "bookings": [shape_booking(b, "owner") for b in bk[:300]], "amenities": AMENITIES, "includes": INCLUDES, "kinds": Property.KINDS,
           "waiting": Booking.objects.filter(Q(room__prop__owner=u) | Q(tour__owner=u), status="pending").count(), "is_mod": _is_mod(u)}
    return Response(out)


def _my_prop(u, pk):
    return Property.objects.filter(pk=pk, owner=u).first()


def _my_tour(u, pk):
    return Tour.objects.filter(pk=pk, owner=u).first()


def _company_for(u, cid):
    try:
        return _companies(u).filter(pk=_int(cid, 0, 10 ** 9)).first()
    except Exception:
        return None


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def prop_save(request, pk=None):
    u = request.user
    p = _my_prop(u, pk) if pk else None
    if pk and not p:
        return _err("Not found.", 404)
    if request.method == "DELETE":
        if p.rooms.filter(bookings__status__in=HELD, bookings__end__gte=timezone.localdate()).exists():
            return _err("This place has upcoming bookings. Hide it instead, or finish the bookings first.")
        p.delete(); return Response({"ok": True})
    v = request.data
    if not p:
        c = _company_for(u, v.get("company"))
        if not c:
            return _err("Only KYC-verified companies can list a place. Verify your company on your company page first.")
        if Property.objects.filter(owner=u).count() >= 20:
            return _err("You can list up to 20 places.")
        p = Property(company=c, owner=u)
    name, city = _t(v.get("name", p.name), 120), _t(v.get("city", p.city), 60)
    if len(name) < 3 or len(city) < 2:
        return _err("Give the place a name and a city.")
    p.name, p.city = name, city
    p.kind = v.get("kind") if v.get("kind") in dict(Property.KINDS) else p.kind
    p.stars = _int(v.get("stars", p.stars), 0, 7, 0)
    for f, n in (("area", 80), ("address", 240), ("phone", 30), ("whatsapp", 30), ("check_in", 10), ("check_out", 10)):
        if f in v:
            setattr(p, f, _t(v.get(f), n))
    for f, n in (("about", 4000), ("policies", 2000)):
        if f in v:
            setattr(p, f, _t(v.get(f), n))
    if "map_url" in v:
        m = _t(v.get("map_url"), 300)
        p.map_url = m if m.startswith(("https://maps.google", "https://www.google.com/maps", "https://goo.gl/maps", "https://maps.app.goo.gl", "https://www.openstreetmap.org")) else ""
    if "amenities" in v:
        p.amenities = _clean_list(v.get("amenities"), AMENITIES)
    if "hidden" in v and p.status in ("approved", "hidden"):
        p.status = "hidden" if v.get("hidden") else "approved"
    if not p.slug:
        p.slug = _slug(Property, p.name + "-" + p.city)
    if not p.pk:
        p.status = "pending"
    elif p.status == "rejected" and v.get("resubmit"):
        p.status = "pending"
    p.save()
    return Response(shape_prop(p, mine=True), status=201 if not pk else 200)


def _save_photo(f, folder, oid):
    if not f:
        return None, "Choose a photo."
    if f.size > 10 * 1024 * 1024:
        return None, "The photo is over 10 MB."
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); im.load()
    except Exception:
        return None, "That file is not a photo we can read."
    im = ImageOps.exif_transpose(im).convert("RGB")
    im = ImageOps.fit(im, (1280, 854), method=Image.LANCZOS)
    rel = os.path.join(folder, timezone.localdate().strftime("%Y%m"), "%d_%s.webp" % (oid, secrets.token_hex(6)))
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=80)
    return rel, None


def _photos(request, obj, folder, limit=MAX_PHOTOS):
    if request.method == "DELETE":
        rel = str(request.data.get("photo") or request.GET.get("photo") or "")
        if rel in obj.photos:
            obj.photos = [x for x in obj.photos if x != rel]; obj.save(update_fields=["photos"])
            try:
                os.remove(os.path.join(str(settings.MEDIA_ROOT), rel))
            except OSError:
                pass
        return None
    if request.data.get("cover") in obj.photos:
        c = request.data.get("cover"); obj.photos = [c] + [x for x in obj.photos if x != c]; obj.save(update_fields=["photos"]); return None
    if len(obj.photos) >= limit:
        return "You can add up to %d photos." % limit
    rel, bad = _save_photo(request.FILES.get("photo"), folder, obj.pk)
    if bad:
        return bad
    obj.photos = list(obj.photos) + [rel]; obj.save(update_fields=["photos"])
    return None


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def prop_photo(request, pk):
    p = _my_prop(request.user, pk)
    if not p:
        return _err("Not found.", 404)
    bad = _photos(request, p, "travel/hotels")
    return _err(bad) if bad else Response(shape_prop(p, mine=True))


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def room_save(request, pk, rid=None):
    p = _my_prop(request.user, pk)
    if not p:
        return _err("Not found.", 404)
    r = Room.objects.filter(pk=rid, prop=p).first() if rid else None
    if rid and not r:
        return _err("Room not found.", 404)
    if request.method == "DELETE":
        if r.bookings.filter(status__in=HELD, end__gte=timezone.localdate()).exists():
            r.active = False; r.save(update_fields=["active"]); return Response({"ok": True, "hidden": True})
        r.delete(); return Response({"ok": True})
    v = request.data
    if not r:
        if p.rooms.count() >= 30:
            return _err("Up to 30 room types per place.")
        r = Room(prop=p)
    name = _t(v.get("name", r.name), 80)
    price = _int(v.get("price", r.price or 0), 0, 10 ** 7, 0)
    if len(name) < 2 or price < 100:
        return _err("Give the room a name and a price per night (Rs 100 or more).")
    r.name, r.price = name, price
    r.adults = _int(v.get("adults", r.adults), 1, 20, 2)
    r.count = _int(v.get("count", r.count), 1, 500, 1)
    r.beds = _t(v.get("beds", r.beds), 80); r.about = _t(v.get("about", r.about), 300)
    if "amenities" in v:
        r.amenities = _clean_list(v.get("amenities"), AMENITIES)
    if "active" in v:
        r.active = bool(v.get("active"))
    r.save()
    return Response(shape_prop(p, mine=True))


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def room_photo(request, pk, rid):
    p = _my_prop(request.user, pk)
    r = Room.objects.filter(pk=rid, prop=p).first() if p else None
    if not r:
        return _err("Not found.", 404)
    bad = _photos(request, r, "travel/rooms", 6)
    return _err(bad) if bad else Response(shape_prop(p, mine=True))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def calendar(request, pk):
    p = _my_prop(request.user, pk)
    if not p:
        return _err("Not found.", 404)
    m = re.fullmatch(r"(\d{4})-(\d{2})", request.GET.get("month") or "")
    first = date(int(m.group(1)), int(m.group(2)), 1) if m else timezone.localdate().replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    days = nights(first, nxt)
    rows = []
    for r in p.rooms.all():
        bk = list(r.bookings.filter(status__in=HELD, start__lt=nxt, end__gt=first).values_list("start", "end", "qty", "status", "name", "code"))
        bl = list(r.blocks.filter(start__lt=nxt, end__gt=first).values_list("id", "start", "end", "count", "note"))
        cells = []
        for d in days:
            used = sum(q for s, e, q, *_ in bk if s <= d < e); shut = sum(c for _i, s, e, c, _n in bl if s <= d < e)
            cells.append({"d": d.isoformat(), "booked": used, "blocked": shut, "free": max(0, r.count - used - shut),
                          "who": [{"n": n, "c": c, "s": st} for s, e, q, st, n, c in bk if s <= d < e][:4]})
        rows.append({"room": r.id, "name": r.name, "count": r.count, "days": cells,
                     "blocks": [{"id": i, "start": s.isoformat(), "end": e.isoformat(), "count": c, "note": n} for i, s, e, c, n in bl]})
    return Response({"month": first.strftime("%Y-%m"), "label": first.strftime("%B %Y"), "rows": rows})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def block(request, pk):
    p = _my_prop(request.user, pk)
    if not p:
        return _err("Not found.", 404)
    if request.method == "DELETE":
        Block.objects.filter(pk=_int(request.data.get("id") or request.GET.get("id"), 0, 10 ** 9), room__prop=p).delete()
        return Response({"ok": True})
    r = Room.objects.filter(pk=_int(request.data.get("room"), 0, 10 ** 9), prop=p).first()
    a, b = _date(request.data.get("start")), _date(request.data.get("end"))
    if not r or not a or not b or b <= a or (b - a).days > 366:
        return _err("Pick the room and the dates.")
    n = _int(request.data.get("count"), 1, r.count, 1)
    if free_rooms(r, a, b) < n:
        return _err("Not that many rooms are free on those dates.")
    Block.objects.create(room=r, start=a, end=b, count=n, note=_t(request.data.get("note"), 120))
    return Response({"ok": True})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def tour_save(request, pk=None):
    u = request.user
    t = _my_tour(u, pk) if pk else None
    if pk and not t:
        return _err("Not found.", 404)
    if request.method == "DELETE":
        if t.bookings.filter(status__in=HELD, start__gte=timezone.localdate()).exists():
            return _err("This tour has upcoming bookings. Hide it instead.")
        t.delete(); return Response({"ok": True})
    v = request.data
    if not t:
        c = _company_for(u, v.get("company"))
        if not c:
            return _err("Only KYC-verified companies can sell tours. Verify your company on your company page first.")
        if Tour.objects.filter(owner=u).count() >= 40:
            return _err("You can list up to 40 tours.")
        t = Tour(company=c, owner=u)
    title, dest = _t(v.get("title", t.title), 140), _t(v.get("destination", t.destination), 80)
    price = _int(v.get("price", t.price or 0), 0, 10 ** 8, 0)
    if len(title) < 4 or len(dest) < 2 or price < 100:
        return _err("Give the tour a title, a destination and a price per person.")
    t.title, t.destination, t.price = title, dest, price
    t.child_price = _int(v.get("child_price", t.child_price), 0, 10 ** 8, 0)
    t.days = _int(v.get("days", t.days), 1, 60, 3); t.nights = _int(v.get("nights", t.nights), 0, 60, max(0, t.days - 1))
    t.max_group = _int(v.get("max_group", t.max_group), 1, 500, 20)
    for f, n in (("start_city", 60), ("phone", 30), ("whatsapp", 30)):
        if f in v:
            setattr(t, f, _t(v.get(f), n))
    if "about" in v:
        t.about = _t(v.get("about"), 5000)
    if "includes" in v:
        t.includes = _clean_list(v.get("includes"), INCLUDES)
    if "excludes" in v:
        t.excludes = _clean_list(v.get("excludes"), None, 15, 80)
    if "itinerary" in v and isinstance(v.get("itinerary"), list):
        t.itinerary = [{"t": _t(x.get("t"), 100), "x": _t(x.get("x"), 1000)} for x in v.get("itinerary")[:60] if isinstance(x, dict) and _t(x.get("t"), 100)]
    if "departures" in v and isinstance(v.get("departures"), list):
        deps = []
        for x in v.get("departures")[:60]:
            dd = _date(x.get("d") if isinstance(x, dict) else None)
            if dd:
                deps.append({"d": dd.isoformat(), "seats": _int(x.get("seats"), 1, 2000, t.max_group)})
        t.departures = sorted({d["d"]: d for d in deps}.values(), key=lambda x: x["d"])
    if "hidden" in v and t.status in ("approved", "hidden"):
        t.status = "hidden" if v.get("hidden") else "approved"
    if not t.slug:
        t.slug = _slug(Tour, t.title)
    if not t.pk:
        t.status = "pending"
    elif t.status == "rejected" and v.get("resubmit"):
        t.status = "pending"
    t.save()
    return Response(shape_tour(t, mine=True), status=201 if not pk else 200)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def tour_photo(request, pk):
    t = _my_tour(request.user, pk)
    if not t:
        return _err("Not found.", 404)
    bad = _photos(request, t, "travel/tours")
    return _err(bad) if bad else Response(shape_tour(t, mine=True))


NEXT = {"confirm": ("pending",), "decline": ("pending",), "checkin": ("confirmed",), "checkout": ("checked_in", "confirmed"), "noshow": ("confirmed",), "cancel": ("confirmed",)}
TO = {"confirm": "confirmed", "decline": "declined", "checkin": "checked_in", "checkout": "done", "noshow": "no_show", "cancel": "cancelled"}
SAY = {"confirmed": "✅ Your booking %s at %s is confirmed. Pay at arrival.", "declined": "Sorry, %s at %s could not be accepted. Try other dates or another place.",
       "done": "Thanks for staying with %s at %s! You can now leave a review.", "cancelled": "Your booking %s at %s was cancelled by the owner."}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def booking_action(request, pk):
    u = request.user
    b = Booking.objects.filter(pk=pk).filter(Q(room__prop__owner=u) | Q(tour__owner=u)).select_related("room__prop", "tour", "guest").first()
    if not b:
        return _err("Booking not found.", 404)
    act = request.data.get("action")
    if act not in NEXT or b.status not in NEXT[act]:
        return _err("Not possible for a booking that is %s." % b.get_status_display().lower())
    if act == "confirm":
        if b.kind == "room":
            if free_rooms(b.room, b.start, b.end, skip=b.pk) < b.qty:
                return _err("Those rooms are no longer free on these dates (another booking or a block). Decline it, or free a room first.")
        else:
            left = seats_left(b.tour, b.start, skip=b.pk)
            if left is not None and left < b.qty + b.children:
                return _err("Not enough seats left on that date.")
    b.status = TO[act]
    b.owner_note = _t(request.data.get("note"), 300) or b.owner_note
    b.save(update_fields=["status", "owner_note", "updated_at"])
    place = b.room.prop.name if b.kind == "room" else b.tour.title
    if b.status in SAY:
        _notify(b.guest, SAY[b.status] % (b.code, place) + ((" Note: " + b.owner_note) if b.owner_note and b.status in ("confirmed", "declined") else ""), "/my-trips#b%d" % b.id)
    return Response(shape_booking(b, "owner"))


# ---------------------------------------------------------------- team review of new listings
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def review_queue(request):
    if not _is_mod(request.user):
        return _err("Team only.", 403)
    if request.method == "GET":
        return Response({"properties": [shape_prop(p, mine=True) for p in Property.objects.filter(status="pending").select_related("company")[:50]],
                         "tours": [shape_tour(t, mine=True) for t in Tour.objects.filter(status="pending").select_related("company")[:50]]})
    kind, pk, ok = request.data.get("kind"), _int(request.data.get("id"), 0, 10 ** 9), bool(request.data.get("approve"))
    obj = (Property if kind == "property" else Tour).objects.filter(pk=pk).first()
    if not obj:
        return _err("Not found.", 404)
    obj.status = "approved" if ok else "rejected"; obj.review_note = _t(request.data.get("note"), 300)
    if "featured" in request.data:
        obj.featured = bool(request.data.get("featured"))
    obj.save(update_fields=["status", "review_note", "featured"])
    name = obj.name if kind == "property" else obj.title
    _notify(obj.owner, ("✅ %s is now live on XpertCreation." % name) if ok else ("%s was not approved: %s" % (name, obj.review_note or "please check the details")), "/travel-manage")
    return Response({"ok": True})
