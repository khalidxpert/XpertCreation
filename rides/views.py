"""XpertCreation Rides (women only): riders ask for a ride on the map, nearby online women drivers get it,
the first to accept takes it, both follow each other live. Cash to the driver. Drivers need an approved
ID check plus licence and vehicle papers, approved by the team. Riders state that they are women."""
import math
import os
import re
import secrets
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import VEHICLES, Driver, DriverDoc, Fare, Report, Ride, Rider

DEFAULT_FARES = {"bike": (60, 25, 100), "rickshaw": (90, 40, 150), "car": (150, 65, 250)}   # base, per km, minimum (Rs)
RADIUS_KM = 7.0           # how far away a driver still gets a request
SEARCH_MIN = 5            # a request with no driver for this long expires
FRESH_SEC = 120           # a driver whose phone has not sent a location for this long is not shown as online
ROAD = 1.3                # straight line to road distance
ACTIVE = (Ride.SEARCHING, Ride.ACCEPTED, Ride.ARRIVED, Ride.STARTED)
EMERGENCY = [{"label": "Police", "number": "15"}, {"label": "Rescue / ambulance", "number": "1122"},
             {"label": "Women helpline (Punjab)", "number": "1043"}, {"label": "XpertCreation team (WhatsApp)", "number": "+923009462916"}]
MAGIC = [(b"%PDF", "pdf"), (b"\xff\xd8\xff", "jpg"), (b"\x89PNG", "png")]


def _docs_dir():
    try:
        from companies.views import DOCS
        return os.path.join(DOCS, "rides")
    except Exception:
        return os.environ.get("XC_RIDES_DOCS", "/var/lib/gunicorn-academy/kyc_docs/rides")


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _num(v, lo, hi):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if lo <= x <= hi and not math.isnan(x) else None


def _phone(v):
    p = re.sub(r"[^\d+]", "", str(v or ""))[:20]
    return p if len(re.sub(r"\D", "", p)) >= 10 else ""


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _kyc(u):
    k = getattr(u, "person_kyc", None)
    try:
        if k and k.status == "approved":
            return True
    except Exception:
        pass
    try:
        from network.models import ProProfile
        return ProProfile.objects.filter(user=u, verified=True).exists()
    except Exception:
        return False


def _name(u):
    return (getattr(u, "full_name", "") or u.username or "Member").strip()


def _avatar(u):
    try:
        from accounts.views import avatar_url
        return avatar_url(u.avatar) or ""
    except Exception:
        return ""


def _notify(user, text, link="/rides"):
    try:
        from notifications.views import notify
        notify(user, "rides", text, link)
    except Exception:
        pass


def _admins(text, link="/rides#team"):
    try:
        from notifications.views import notify_admins
        notify_admins("rides", text, link)
    except Exception:
        pass


def _km(a_lat, a_lng, b_lat, b_lng):
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lng - a_lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _fares():
    have = {f.vehicle: f for f in Fare.objects.all()}
    for v, (b, k, m) in DEFAULT_FARES.items():
        if v not in have:
            have[v] = Fare.objects.create(vehicle=v, base=b, per_km=k, minimum=m)
    return have


def _price(vehicle, km):
    f = _fares()[vehicle]
    return int(max(f.minimum, round((f.base + f.per_km * km) / 10.0) * 10))


def _expire():
    Ride.objects.filter(status=Ride.SEARCHING, created_at__lt=timezone.now() - timedelta(minutes=SEARCH_MIN)).update(status=Ride.EXPIRED, ended_at=timezone.now())


def _fresh():
    return timezone.now() - timedelta(seconds=FRESH_SEC)


def _driver_out(d, full=False):
    o = {"id": d.id, "status": d.status, "status_label": dict(Driver.STATES)[d.status], "vehicle": d.vehicle, "vehicle_label": dict(VEHICLES)[d.vehicle],
         "make": d.make, "plate": d.plate, "rating": round(d.rating, 1), "ratings": d.ratings, "rides_done": d.rides_done,
         "name": _name(d.user), "avatar": _avatar(d.user), "online": bool(d.online and d.loc_at and d.loc_at > _fresh())}
    if full:
        o.update({"phone": d.phone, "city": d.city, "licence_no": d.licence_no, "note": d.note,
                  "docs": [{"id": x.id, "kind": x.kind, "kind_label": dict(DriverDoc.KINDS)[x.kind], "name": x.name} for x in d.docs.all()]})
    return o


def _ride_out(r, viewer):
    is_rider = viewer.is_authenticated and r.rider_id == viewer.id
    is_driver = viewer.is_authenticated and r.driver_id and r.driver.user_id == viewer.id
    o = {"id": r.id, "status": r.status, "status_label": dict(Ride.STATES)[r.status], "vehicle": r.vehicle, "vehicle_label": dict(VEHICLES)[r.vehicle],
         "pickup": {"lat": r.p_lat, "lng": r.p_lng, "text": r.p_text}, "drop": {"lat": r.d_lat, "lng": r.d_lng, "text": r.d_text},
         "km": round(r.km, 1), "fare": r.fare, "note": r.note, "created": r.created_at.isoformat(),
         "ended": r.ended_at.isoformat() if r.ended_at else "", "cancel_by": r.cancel_by, "cancel_reason": r.cancel_reason,
         "me": "rider" if is_rider else "driver" if is_driver else "", "rider_stars": r.rider_stars, "driver_stars": r.driver_stars,
         "track": "/rides#track-" + r.token if is_rider else ""}
    live = r.status in (Ride.ACCEPTED, Ride.ARRIVED, Ride.STARTED)
    if r.driver_id:
        d = r.driver
        o["driver"] = _driver_out(d)
        if live:
            o["driver"]["phone"] = d.phone
            if d.lat is not None and d.loc_at and d.loc_at > timezone.now() - timedelta(minutes=5):
                o["driver"]["lat"], o["driver"]["lng"] = d.lat, d.lng
                tgt = (r.p_lat, r.p_lng) if r.status in (Ride.ACCEPTED, Ride.ARRIVED) else (r.d_lat, r.d_lng)
                o["eta_min"] = max(1, int(round(_km(d.lat, d.lng, tgt[0], tgt[1]) * ROAD / 22.0 * 60)))
    rider = getattr(r.rider, "ride_rider", None)
    o["rider"] = {"name": _name(r.rider), "avatar": _avatar(r.rider), "rating": round(rider.rating, 1) if rider else 0,
                  "phone": rider.phone if (rider and live and (is_driver or _staff(viewer))) else ""}
    return o


def _active_ride(u):
    _expire()
    r = Ride.objects.filter(rider=u, status__in=ACTIVE).select_related("driver__user", "rider").first()
    if r:
        return r
    d = getattr(u, "ride_driver", None)
    if d:
        return Ride.objects.filter(driver=d, status__in=ACTIVE[1:]).select_related("driver__user", "rider").first()
    return None


# ------------------------------------------------------------------ overview
@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    u = request.user
    f = _fares()
    out = {"vehicles": [{"key": k, "label": l, "base": f[k].base, "per_km": f[k].per_km, "minimum": f[k].minimum, "active": f[k].active} for k, l in VEHICLES],
           "emergency": EMERGENCY, "radius_km": RADIUS_KM, "me": None}
    if u.is_authenticated:
        rider = getattr(u, "ride_rider", None) if hasattr(u, "ride_rider") else None
        try:
            d = u.ride_driver
        except Driver.DoesNotExist:
            d = None
        r = _active_ride(u)
        out["me"] = {"name": _name(u), "kyc": _kyc(u), "staff": _staff(u),
                     "phone": getattr(u, "whatsapp", "") or getattr(u, "phone", ""),
                     "rider": {"phone": rider.phone, "blocked": rider.blocked} if rider else None,
                     "driver": _driver_out(d, True) if d else None,
                     "active": _ride_out(r, u) if r else None}
    return Response(out)


@api_view(["GET"])
@permission_classes([AllowAny])
def nearby(request):
    """Online drivers near a point, for the map: counts per vehicle and rough positions (about 200 m off on purpose)."""
    lat, lng = _num(request.GET.get("lat"), -90, 90), _num(request.GET.get("lng"), -180, 180)
    if lat is None or lng is None:
        return _err("Location needed.")
    dl = RADIUS_KM / 111.0
    rows = Driver.objects.filter(status=Driver.APPROVED, online=True, loc_at__gt=_fresh(), lat__range=(lat - dl, lat + dl), lng__range=(lng - dl * 1.3, lng + dl * 1.3))
    counts, pts = {k: 0 for k, _ in VEHICLES}, []
    for d in rows[:200]:
        if _km(lat, lng, d.lat, d.lng) <= RADIUS_KM and not Ride.objects.filter(driver=d, status__in=ACTIVE[1:]).exists():
            counts[d.vehicle] += 1
            pts.append({"v": d.vehicle, "lat": round(d.lat, 3), "lng": round(d.lng, 3)})
    return Response({"counts": counts, "drivers": pts[:60]})


@api_view(["GET"])
@permission_classes([AllowAny])
def quote(request):
    g = request.GET
    p = [_num(g.get(k), lo, hi) for k, lo, hi in (("p_lat", -90, 90), ("p_lng", -180, 180), ("d_lat", -90, 90), ("d_lng", -180, 180))]
    if None in p:
        return _err("Set pickup and drop-off.")
    km = _km(*p) * ROAD
    f = _fares()
    return Response({"km": round(km, 1), "minutes": max(1, int(round(km / 22.0 * 60))),
                     "fares": {k: _price(k, km) for k, _ in VEHICLES if f[k].active}})


# ------------------------------------------------------------------ rider
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rider(request):
    d = request.data
    if not d.get("woman"):
        return _err("XpertCreation Rides is for women only. Please confirm that you are a woman.")
    ph = _phone(d.get("phone"))
    if not ph:
        return _err("Enter your phone or WhatsApp number (the driver calls you on it).")
    r, _ = Rider.objects.get_or_create(user=request.user, defaults={"phone": ph})
    r.phone = ph; r.save(update_fields=["phone"])
    return Response({"rider": {"phone": r.phone, "blocked": r.blocked}})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def rides(request):
    u = request.user
    if request.method == "GET":
        _expire()
        mine = Ride.objects.filter(rider=u).select_related("driver__user", "rider").order_by("-id")[:30]
        d = getattr(u, "ride_driver", None) if Driver.objects.filter(user=u).exists() else None
        drove = Ride.objects.filter(driver=d).select_related("driver__user", "rider").order_by("-id")[:30] if d else []
        return Response({"taken": [_ride_out(r, u) for r in mine], "driven": [_ride_out(r, u) for r in drove]})
    rd = Rider.objects.filter(user=u).first()
    if not rd:
        return _err("First confirm that you are a woman and add your phone number.", 403)
    if rd.blocked:
        return _err("Your rides are paused. Please contact the XpertCreation team.", 403)
    if _active_ride(u):
        return _err("You already have a ride going.")
    k = "rides_req_%d" % u.id
    if cache.get(k, 0) >= 12:
        return _err("Too many requests in the last hour. Please wait a little.", 429)
    d = request.data
    v = d.get("vehicle")
    f = _fares()
    if v not in f or not f[v].active:
        return _err("Choose car, rickshaw or bike.")
    p = [_num(d.get(x), lo, hi) for x, lo, hi in (("p_lat", -90, 90), ("p_lng", -180, 180), ("d_lat", -90, 90), ("d_lng", -180, 180))]
    if None in p:
        return _err("Set pickup and drop-off on the map.")
    km = _km(*p) * ROAD
    if km < 0.3:
        return _err("Pickup and drop-off are too close.")
    if km > 150:
        return _err("That trip is too long for the pilot (over 150 km).")
    r = Ride.objects.create(rider=u, vehicle=v, p_lat=p[0], p_lng=p[1], d_lat=p[2], d_lng=p[3], km=km, fare=_price(v, km),
                            p_text=_txt(d.get("p_text"), 160), d_text=_txt(d.get("d_text"), 160), note=_txt(d.get("note"), 200),
                            token=secrets.token_urlsafe(12)[:16])
    cache.set(k, cache.get(k, 0) + 1, 3600)
    return Response({"ride": _ride_out(r, u)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ride(request, pk):
    _expire()
    r = Ride.objects.filter(pk=pk).select_related("driver__user", "rider").first()
    u = request.user
    if not r or not (r.rider_id == u.id or (r.driver_id and r.driver.user_id == u.id) or _staff(u)):
        return _err("Ride not found.", 404)
    return Response({"ride": _ride_out(r, u)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ride_act(request, pk, act):
    u = request.user; d = request.data; now = timezone.now()
    r = Ride.objects.filter(pk=pk).select_related("driver__user", "rider").first()
    if not r:
        return _err("Ride not found.", 404)
    me_driver = Driver.objects.filter(user=u).first()
    is_rider = r.rider_id == u.id
    is_driver = bool(me_driver and r.driver_id == me_driver.id)

    if act == "accept":
        if not me_driver or me_driver.status != Driver.APPROVED:
            return _err("Only approved drivers can accept rides.", 403)
        if r.rider_id == u.id:
            return _err("You cannot accept your own ride.")
        if me_driver.vehicle != r.vehicle or me_driver.id in (r.skip or []):
            return _err("This ride is not for your vehicle.")
        if Ride.objects.filter(driver=me_driver, status__in=ACTIVE[1:]).exists():
            return _err("Finish your current ride first.")
        n = Ride.objects.filter(pk=r.pk, status=Ride.SEARCHING).update(status=Ride.ACCEPTED, driver=me_driver, accepted_at=now)
        if not n:
            return _err("Another driver took this ride.", 409)
        r.refresh_from_db()
        _notify(r.rider, "%s is coming to pick you up (%s, %s)." % (_name(u), me_driver.make, me_driver.plate))
        return Response({"ride": _ride_out(r, u)})

    if act in ("arrive", "start", "done"):
        if not is_driver:
            return _err("Only this ride's driver can do that.", 403)
        need = {"arrive": Ride.ACCEPTED, "start": Ride.ARRIVED, "done": Ride.STARTED}[act]
        if r.status != need:
            return _err("This ride is %s." % dict(Ride.STATES)[r.status].lower())
        if act == "arrive":
            r.status, r.arrived_at = Ride.ARRIVED, now
            _notify(r.rider, "Your driver has arrived: %s, %s." % (me_driver.make, me_driver.plate))
        elif act == "start":
            r.status, r.started_at = Ride.STARTED, now
        else:
            r.status, r.ended_at = Ride.DONE, now
            Driver.objects.filter(pk=me_driver.pk).update(rides_done=me_driver.rides_done + 1)
            _notify(r.rider, "Ride completed. Please pay Rs %s in cash to the driver and rate your ride." % "{:,}".format(r.fare), "/rides#ride-%d" % r.id)
        r.save()
        return Response({"ride": _ride_out(r, u)})

    if act == "cancel":
        reason = _txt(d.get("reason"), 200)
        if is_rider:
            if r.status not in (Ride.SEARCHING, Ride.ACCEPTED, Ride.ARRIVED):
                return _err("The trip has started; it cannot be cancelled now.")
            r.status, r.cancel_by, r.cancel_reason, r.ended_at = Ride.CANCELLED, "rider", reason, now
            r.save()
            if r.driver_id:
                _notify(r.driver.user, "The rider cancelled the ride.", "/rides#drive")
            return Response({"ride": _ride_out(r, u)})
        if is_driver:
            if r.status == Ride.STARTED:
                r.status, r.cancel_by, r.cancel_reason, r.ended_at = Ride.CANCELLED, "driver", reason, now
                r.save()
                _notify(r.rider, "Your driver ended the ride early. If you need help, use SOS or contact the team.", "/rides#ride-%d" % r.id)
                return Response({"ride": _ride_out(r, u)})
            # before the trip: the request goes back to other drivers
            r.skip = list(set((r.skip or []) + [me_driver.id]))
            r.status, r.driver, r.accepted_at, r.arrived_at, r.created_at = Ride.SEARCHING, None, None, None, now
            r.save()
            _notify(r.rider, "Your driver could not come. We are finding you another driver.", "/rides")
            return Response({"ride": None})
        return _err("Not your ride.", 403)

    if act == "rate":
        s = int(_num(d.get("stars"), 1, 5) or 0)
        if not s or r.status != Ride.DONE:
            return _err("Choose 1 to 5 stars after the ride.")
        if is_rider and r.rider_stars is None:
            r.rider_stars = s; r.save(update_fields=["rider_stars"])
            dr = r.driver
            if dr:
                dr.rating = (dr.rating * dr.ratings + s) / (dr.ratings + 1); dr.ratings += 1; dr.save(update_fields=["rating", "ratings"])
        elif is_driver and r.driver_stars is None:
            r.driver_stars = s; r.save(update_fields=["driver_stars"])
            rd = Rider.objects.filter(user=r.rider).first()
            if rd:
                rd.rating = (rd.rating * rd.ratings + s) / (rd.ratings + 1); rd.ratings += 1; rd.save(update_fields=["rating", "ratings"])
        return Response({"ride": _ride_out(r, u)})

    if act in ("sos", "report"):
        if not (is_rider or is_driver):
            return _err("Not your ride.", 403)
        rep = Report.objects.create(ride=r, by=u, sos=(act == "sos"), text=_txt(d.get("text"), 600),
                                    lat=_num(d.get("lat"), -90, 90), lng=_num(d.get("lng"), -180, 180))
        _admins(("SOS from a ride! " if rep.sos else "Ride report: ") + "%s, ride #%d. Open the Rides team page." % (_name(u), r.id))
        return Response({"ok": True, "emergency": EMERGENCY})
    return _err("Unknown action.", 404)


@api_view(["GET"])
@permission_classes([AllowAny])
def track(request, token):
    """Share-my-trip: anyone with the link sees the driver, the car and where it is - only while the ride is going."""
    r = Ride.objects.filter(token=token).select_related("driver__user", "rider").first()
    if not r or (r.ended_at and r.ended_at < timezone.now() - timedelta(minutes=30)):
        return _err("This trip link has ended.", 404)
    o = {"status": r.status, "status_label": dict(Ride.STATES)[r.status], "vehicle_label": dict(VEHICLES)[r.vehicle],
         "pickup": {"lat": r.p_lat, "lng": r.p_lng, "text": r.p_text}, "drop": {"lat": r.d_lat, "lng": r.d_lng, "text": r.d_text},
         "rider": _name(r.rider).split(" ")[0]}
    if r.driver_id:
        d = r.driver
        o["driver"] = {"name": _name(d.user), "make": d.make, "plate": d.plate, "avatar": _avatar(d.user)}
        if r.status in (Ride.ACCEPTED, Ride.ARRIVED, Ride.STARTED) and d.lat is not None:
            o["driver"]["lat"], o["driver"]["lng"] = d.lat, d.lng
    return Response(o)


# ------------------------------------------------------------------ driver
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def driver(request):
    u = request.user
    d = Driver.objects.filter(user=u).first()
    if request.method == "GET":
        return Response({"driver": _driver_out(d, True) if d else None, "kyc": _kyc(u)})
    if not _kyc(u):
        return _err("Drivers need an approved ID check first. Open Get verified, upload your CNIC, then come back.", 403)
    x = request.data
    if not x.get("woman"):
        return _err("Only women can drive on XpertCreation Rides.")
    if d and d.status in (Driver.PENDING, Driver.SUSPENDED):
        return _err("Your application is %s. You cannot change it now." % dict(Driver.STATES)[d.status].lower())
    v = x.get("vehicle")
    if v not in dict(VEHICLES):
        return _err("Choose car, rickshaw or bike.")
    ph, city, make, plate = _phone(x.get("phone")), _txt(x.get("city"), 60), _txt(x.get("make"), 60), _txt(x.get("plate"), 20).upper()
    if not ph or not city or not make or not plate:
        return _err("Fill in phone, city, vehicle and number plate.")
    vals = {"phone": ph, "city": city, "vehicle": v, "make": make, "plate": plate, "licence_no": _txt(x.get("licence_no"), 30)}
    if d:
        for k, val in vals.items():
            setattr(d, k, val)
        if d.status == Driver.APPROVED and (d.vehicle != v or d.plate != plate):
            d.status, d.online = Driver.PENDING, False     # a new vehicle is checked again
            _admins("A driver changed her vehicle: %s. Please review." % _name(u))
        d.save()
    else:
        d = Driver.objects.create(user=u, **vals)
    return Response({"driver": _driver_out(d, True)})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def driver_docs(request):
    d = Driver.objects.filter(user=request.user).first()
    if not d:
        return _err("Fill in your driver details first.", 404)
    if d.status == Driver.PENDING:
        return _err("Your papers are being reviewed.")
    if request.method == "DELETE":
        x = d.docs.filter(pk=request.data.get("doc")).first()
        if x:
            try:
                os.remove(os.path.join(_docs_dir(), x.path))
            except OSError:
                pass
            x.delete()
        return Response({"driver": _driver_out(d, True)})
    f = request.FILES.get("file"); kind = request.data.get("kind")
    if not f or kind not in dict(DriverDoc.KINDS):
        return _err("Choose the paper type and a file.")
    if f.size > 5 * 1024 * 1024:
        return _err("That file is over 5 MB.")
    if d.docs.count() >= 8:
        return _err("You can upload up to 8 files.")
    head = f.read(8); f.seek(0)
    ext = next((e for m, e in MAGIC if head.startswith(m)), None)
    if not ext:
        return _err("Use a PDF, JPG or PNG file.")
    rel = "d%d/%s.%s" % (d.id, secrets.token_hex(12), ext)
    full = os.path.join(_docs_dir(), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as out:
        for ch in f.chunks():
            out.write(ch)
    os.chmod(full, 0o600)
    DriverDoc.objects.create(driver=d, kind=kind, path=rel, name=_txt(f.name, 120), size=f.size)
    return Response({"driver": _driver_out(d, True)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def driver_doc_file(request, doc):
    x = DriverDoc.objects.filter(pk=doc).select_related("driver").first()
    if not x or not (x.driver.user_id == request.user.id or _staff(request.user)):
        raise Http404
    full = os.path.join(_docs_dir(), x.path)
    if not os.path.exists(full):
        raise Http404
    r = FileResponse(open(full, "rb"), as_attachment=False, filename=x.name or os.path.basename(full))
    r["X-Content-Type-Options"] = "nosniff"; r["Cache-Control"] = "private, no-store"
    return r


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def driver_submit(request):
    d = Driver.objects.filter(user=request.user).first()
    if not d:
        return _err("Fill in your driver details first.", 404)
    if d.status not in (Driver.DRAFT, Driver.REJECTED):
        return _err("Your application is %s." % dict(Driver.STATES)[d.status].lower())
    if not _kyc(request.user):
        return _err("Your ID check (Get verified) must be approved first.", 403)
    kinds = set(d.docs.values_list("kind", flat=True))
    miss = [l for k, l in DriverDoc.KINDS[:3] if k not in kinds]
    if miss:
        return _err("Please upload: " + ", ".join(miss) + ".")
    d.status, d.note = Driver.PENDING, ""; d.save(update_fields=["status", "note", "updated_at"])
    _admins("New woman driver application: %s (%s, %s)." % (_name(request.user), d.city, dict(VEHICLES)[d.vehicle]))
    return Response({"driver": _driver_out(d, True)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def driver_loc(request):
    """The driver's phone sends this every few seconds while she is online. Going offline clears her location."""
    d = Driver.objects.filter(user=request.user).first()
    if not d or d.status != Driver.APPROVED:
        return _err("Only approved drivers can go online.", 403)
    x = request.data
    if "online" in x:
        d.online = bool(x.get("online"))
    lat, lng = _num(x.get("lat"), -90, 90), _num(x.get("lng"), -180, 180)
    if d.online and lat is not None and lng is not None:
        d.lat, d.lng, d.loc_at = lat, lng, timezone.now()
    if not d.online and not Ride.objects.filter(driver=d, status__in=ACTIVE[1:]).exists():
        d.lat = d.lng = d.loc_at = None
    d.save(update_fields=["online", "lat", "lng", "loc_at", "updated_at"])
    return Response({"online": d.online})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def driver_feed(request):
    """Ride requests near an online driver, nearest first, plus her current ride."""
    _expire()
    d = Driver.objects.filter(user=request.user).first()
    if not d or d.status != Driver.APPROVED:
        return _err("Only approved drivers see ride requests.", 403)
    cur = Ride.objects.filter(driver=d, status__in=ACTIVE[1:]).select_related("driver__user", "rider").first()
    if cur:
        return Response({"current": _ride_out(cur, request.user), "requests": []})
    if not d.online or d.lat is None:
        return Response({"current": None, "requests": []})
    dl = RADIUS_KM / 111.0
    qs = Ride.objects.filter(status=Ride.SEARCHING, vehicle=d.vehicle, p_lat__range=(d.lat - dl, d.lat + dl),
                             p_lng__range=(d.lng - dl * 1.3, d.lng + dl * 1.3)).exclude(rider=request.user).select_related("rider")
    out = []
    for r in qs[:50]:
        if d.id in (r.skip or []):
            continue
        away = _km(d.lat, d.lng, r.p_lat, r.p_lng)
        if away <= RADIUS_KM:
            o = _ride_out(r, request.user); o["away_km"] = round(away * ROAD, 1); out.append(o)
    out.sort(key=lambda o: o["away_km"])
    return Response({"current": None, "requests": out[:10]})


# ------------------------------------------------------------------ team
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    if not _staff(request.user):
        return _err("Team only.", 403)
    _expire()
    u = request.user
    since = timezone.now() - timedelta(days=30)
    ds = Driver.objects.select_related("user").order_by("-updated_at")
    st = Ride.objects.filter(created_at__gte=since).values("status").annotate(n=Count("id"))
    return Response({
        "pending": [_driver_out(d, True) | {"user": _name(d.user), "kyc": _kyc(d.user)} for d in ds.filter(status=Driver.PENDING)],
        "drivers": [_driver_out(d, True) | {"user": _name(d.user)} for d in ds.exclude(status__in=(Driver.PENDING, Driver.DRAFT))[:200]],
        "reports": [{"id": x.id, "sos": x.sos, "text": x.text, "by": _name(x.by), "ride": x.ride_id, "lat": x.lat, "lng": x.lng, "when": x.created_at.isoformat()}
                    for x in Report.objects.filter(handled=False).select_related("by").order_by("-id")[:50]],
        "rides": [_ride_out(r, u) for r in Ride.objects.select_related("driver__user", "rider").order_by("-id")[:40]],
        "stats": {x["status"]: x["n"] for x in st},
        "online": Driver.objects.filter(status=Driver.APPROVED, online=True, loc_at__gt=_fresh()).count(),
        "fares": [{"vehicle": f.vehicle, "base": f.base, "per_km": f.per_km, "minimum": f.minimum, "active": f.active} for f in _fares().values()],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_act(request, kind, pk):
    u = request.user
    if not _staff(u):
        return _err("Team only.", 403)
    x = request.data; act = x.get("act")
    if kind == "driver":
        d = Driver.objects.filter(pk=pk).select_related("user").first()
        if not d:
            return _err("Driver not found.", 404)
        note = _txt(x.get("note"), 300)
        if act == "approve":
            d.status = Driver.APPROVED
            _notify(d.user, "You are approved as an XpertCreation Rides driver. Go online on the Drive tab to get rides.", "/rides#drive")
        elif act == "reject":
            d.status, d.online = Driver.REJECTED, False
            _notify(d.user, "Your driver application was not approved: " + (note or "please check your papers."), "/rides#drive")
        elif act == "suspend":
            d.status, d.online = Driver.SUSPENDED, False
            _notify(d.user, "Your driving on XpertCreation Rides is paused. " + note, "/rides#drive")
        else:
            return _err("Unknown action.")
        d.note, d.reviewed_by, d.reviewed_at = note, u, timezone.now()
        d.save()
        return Response({"ok": True})
    if kind == "fare":
        f = Fare.objects.filter(vehicle=x.get("vehicle")).first()
        if not f:
            return _err("Unknown vehicle.")
        for k in ("base", "per_km", "minimum"):
            n = _num(x.get(k), 0, 100000)
            if n is not None:
                setattr(f, k, int(n))
        if "active" in x:
            f.active = bool(x.get("active"))
        f.save()
        return Response({"ok": True})
    if kind == "report":
        Report.objects.filter(pk=pk).update(handled=True)
        return Response({"ok": True})
    if kind == "rider":
        rd = Rider.objects.filter(user_id=pk).first()
        if not rd:
            return _err("Rider not found.", 404)
        rd.blocked = act == "block"; rd.save(update_fields=["blocked"])
        return Response({"ok": True})
    return _err("Unknown.", 404)
