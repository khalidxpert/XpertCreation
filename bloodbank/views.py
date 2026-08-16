import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import (BLOOD_GROUPS, Ask, Donor, Report, Request as BloodRequest,
                     clean_city, distance_km, donors_for)

log = logging.getLogger(__name__)
GROUPS = [g for g, _ in BLOOD_GROUPS]


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")


def _err(msg, code=status.HTTP_400_BAD_REQUEST, **extra):
    p = {"detail": msg}; p.update(extra)
    return Response(p, status=code)


class SearchThrottle(SimpleRateThrottle):
    """Search is signed-in only and rate limited. Between the two, nobody walks
    away with the donor list."""
    scope = "blood_search"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class AskThrottle(SimpleRateThrottle):
    """One person should not be able to ping every donor in the city at once."""
    scope = "blood_ask"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def donor_public(d, phone=None):
    """
    What a searcher is allowed to see.

    The phone number is absent unless the caller passes one in, which only
    happens after the donor has accepted a specific request. The old build
    returned it in every search result, and a single request could walk away
    with two thousand numbers.
    """
    data = {
        "id": d.id,
        "name": d.name,
        "blood_group": d.blood_group,
        "city": d.city,
        "country": d.country,
        "is_verified": d.is_verified,
        "available": d.can_be_asked,
        "allow_call": d.allow_call,
        "allow_whatsapp": d.allow_whatsapp,
        "allow_sms": d.allow_sms,
        "has_whatsapp": bool(d.whatsapp_number or (d.allow_whatsapp and d.phone)),
    }
    if not d.is_eligible and d.eligible_from:
        data["eligible_from"] = d.eligible_from.isoformat()
    if phone:
        data["phone"] = phone
    return data


# ---------------------------------------------------------------- donor profile

@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def me(request):
    d = Donor.objects.filter(user=request.user).first()

    if request.method == "GET":
        if not d:
            return Response({"registered": False})
        return Response({"registered": True, "donor": dict(
            donor_public(d, phone=d.phone),
            last_donation=d.last_donation.isoformat() if d.last_donation else None,
            is_available=d.is_available,
        )})

    if request.method == "DELETE":
        if d:
            d.delete()
        return Response({"detail": "You are no longer listed as a donor."})

    data = request.data
    group = str(data.get("blood_group") or "").upper().strip()
    if group not in GROUPS:
        return _err("Choose a blood group.")

    city = clean_city(data.get("city"))
    if not city:
        return _err("Which city are you in?")

    phone = str(data.get("phone") or "").strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+") or not phone[1:].isdigit() or not (8 <= len(phone[1:]) <= 15):
        return _err("Use international format, for example +923001234567.")

    last = None
    if data.get("last_donation"):
        from datetime import datetime
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                last = datetime.strptime(str(data["last_donation"]).strip(), fmt).date()
                break
            except ValueError:
                continue
        if last is None:
            return _err("Last donation date: use YYYY-MM-DD.")
        if last > timezone.localdate():
            return _err("Last donation cannot be in the future.")

    fields = dict(
        name=str(data.get("name") or "").strip()[:120] or request.user.full_name or "Donor",
        blood_group=group,
        city=city,
        country=clean_city(data.get("country")) or "Pakistan",
        phone=phone,
        last_donation=last,
        # These are the donor's own switches. The previous build stored them
        # and then never wrote them, so nobody could ever turn calls off.
        allow_call=bool(data.get("allow_call", True)),
        allow_whatsapp=bool(data.get("allow_whatsapp", True)),
        allow_sms=bool(data.get("allow_sms", False)),
        is_available=bool(data.get("is_available", True)),
        whatsapp_number=str(data.get("whatsapp_number") or "").strip().replace(" ", "")[:20],
    )

    if d:
        for k, v in fields.items():
            setattr(d, k, v)
        d.save()
    else:
        d = Donor.objects.create(user=request.user, **fields)

    return Response({"registered": True, "donor": donor_public(d, phone=d.phone)})


# ---------------------------------------------------------------- search

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([SearchThrottle])
def search(request):
    """Signed-in only, and never returns a phone number."""
    group = str(request.GET.get("blood_group") or "").upper().strip()
    city = clean_city(request.GET.get("city"))

    qs = Donor.objects.filter(is_available=True, is_blocked=False, user__is_active=True)
    if city:
        qs = qs.filter(city__iexact=city)
    if group:
        if group not in GROUPS:
            return _err("Unknown blood group.")
        # Widen, not narrow: an A+ patient can receive from A+, A-, O+ and O-.
        qs = qs.filter(blood_group__in=donors_for(group))

    qs = qs.select_related("user").order_by("-is_verified", "-updated_at")[:60]
    rows = [donor_public(d) for d in qs if d.is_eligible]

    return Response({"donors": rows, "count": len(rows),
                     "note": "Contact details appear only after a donor accepts your request."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cities(request):
    rows = (Donor.objects.filter(is_available=True, is_blocked=False)
            .values("city").annotate(n=Count("id")).order_by("-n")[:40])
    return Response({"cities": [{"city": r["city"], "donors": r["n"]} for r in rows]})


# ---------------------------------------------------------------- requests

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def requests_view(request):
    if request.method == "GET":
        # Expire on read: cheap, and nothing stale is ever shown.
        BloodRequest.objects.filter(status=BloodRequest.OPEN,
                                    expires_at__lt=timezone.now()).update(status=BloodRequest.EXPIRED)
        qs = (BloodRequest.objects.filter(requester=request.user)
              .annotate(n_asks=Count("asks"),
                        n_yes=Count("asks", filter=Q(asks__status=Ask.ACCEPTED)))
              .order_by("-created_at")[:30])
        return Response({"requests": [{
            "id": r.id, "blood_group": r.blood_group, "units": r.units,
            "city": r.city, "hospital": r.hospital, "urgency": r.urgency,
            "status": r.status, "live": r.is_live,
            "asked": r.n_asks, "accepted": r.n_yes,
            "created": r.created_at.strftime("%d %b %H:%M"),
            "expires": r.expires_at.strftime("%d %b"),
        } for r in qs]})

    data = request.data
    group = str(data.get("blood_group") or "").upper().strip()
    if group not in GROUPS:
        return _err("Choose a blood group.")
    city = clean_city(data.get("city"))
    if not city:
        return _err("Which city?")
    hospital = str(data.get("hospital") or "").strip()[:200]
    if not hospital:
        return _err("Which hospital?")
    phone = str(data.get("contact_phone") or "").strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+") or not phone[1:].isdigit():
        return _err("Contact number: use international format, e.g. +923001234567.")

    open_count = BloodRequest.objects.filter(requester=request.user,
                                             status=BloodRequest.OPEN,
                                             expires_at__gt=timezone.now()).count()
    if open_count >= 3:
        return _err("You already have three open requests. Close one first.")

    r = BloodRequest.objects.create(
        requester=request.user, blood_group=group, city=city, hospital=hospital,
        units=max(1, min(10, int(data.get("units") or 1))),
        urgency=data.get("urgency") if data.get("urgency") in
                ("normal", "urgent", "critical") else "urgent",
        patient_name=str(data.get("patient_name") or "").strip()[:120],
        note=str(data.get("note") or "").strip()[:600],
        contact_phone=phone,
        expires_at=timezone.now() + timedelta(days=BloodRequest.DEFAULT_DAYS),
    )
    return Response({"id": r.id, "detail": "Request created. Now ask matching donors."},
                    status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def close_request(request, pk):
    r = BloodRequest.objects.filter(id=pk, requester=request.user).first()
    if not r:
        return _err("Not found.", code=status.HTTP_404_NOT_FOUND)
    r.status = BloodRequest.FULFILLED if request.data.get("fulfilled") else BloodRequest.CANCELLED
    r.save(update_fields=["status"])
    return Response({"detail": "Closed."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def request_detail(request, pk):
    r = BloodRequest.objects.filter(id=pk, requester=request.user).first()
    if not r:
        return _err("Not found.", code=status.HTTP_404_NOT_FOUND)

    out = []
    for a in r.asks.select_related("donor").order_by("-status", "-created_at"):
        d = a.donor
        # The number is attached here and only here, and only once the donor
        # has said yes to THIS request.
        out.append({
            "ask_id": a.id, "status": a.status,
            "donor": donor_public(d, phone=d.phone if a.phone_visible else None),
            "answered": a.answered_at.strftime("%d %b %H:%M") if a.answered_at else None,
        })
    return Response({
        "request": {"id": r.id, "blood_group": r.blood_group, "city": r.city,
                    "hospital": r.hospital, "status": r.status, "live": r.is_live,
                    "expires": r.expires_at.strftime("%d %b")},
        "asks": out,
    })


# ---------------------------------------------------------------- asking

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AskThrottle])
def ask(request):
    """body: { request: <id>, donor: <id> }"""
    r = BloodRequest.objects.filter(id=request.data.get("request"),
                                    requester=request.user).first()
    if not r:
        return _err("Request not found.", code=status.HTTP_404_NOT_FOUND)
    if not r.is_live:
        return _err("That request is closed.")

    d = Donor.objects.filter(id=request.data.get("donor")).select_related("user").first()
    if not d or not d.can_be_asked:
        return _err("That donor is not available.")
    if d.blood_group not in r.matching_groups():
        return _err("That donor's blood group does not match this request.")
    if d.user_id == request.user.id:
        return _err("That is your own donor profile.")

    a, created = Ask.objects.get_or_create(
        request=r, donor=d, defaults={"requester_ip": client_ip(request)})
    if not created:
        return _err("You have already asked this donor.")

    try:
        from django.core.mail import send_mail
        from django.conf import settings as st
        send_mail(
            "Blood needed: %s in %s" % (r.blood_group, r.city),
            "Someone needs %s blood at %s, %s.\n\n"
            "Urgency: %s\n\n"
            "Open the app to accept or decline. Your phone number is shared only "
            "if you accept.\n\nhttps://xpertcreation.com/blood"
            % (r.blood_group, r.hospital, r.city, r.get_urgency_display()),
            getattr(st, "DEFAULT_FROM_EMAIL", None), [d.user.email], fail_silently=True)
    except Exception:
        log.exception("Could not email donor %s", d.user_id)

    return Response({"detail": "Asked. You will see their number if they accept."},
                    status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inbox(request):
    """Requests waiting on this donor's answer."""
    d = Donor.objects.filter(user=request.user).first()
    if not d:
        return Response({"asks": []})

    BloodRequest.objects.filter(status=BloodRequest.OPEN,
                                expires_at__lt=timezone.now()).update(status=BloodRequest.EXPIRED)

    qs = (Ask.objects.filter(donor=d).select_related("request", "request__requester")
          .order_by("status", "-created_at")[:40])
    return Response({"asks": [{
        "id": a.id, "status": a.status,
        "request": {
            "blood_group": a.request.blood_group, "units": a.request.units,
            "city": a.request.city, "hospital": a.request.hospital,
            "urgency": a.request.urgency, "note": a.request.note,
            "live": a.request.is_live,
            "created": a.request.created_at.strftime("%d %b %H:%M"),
            # Shown only after accepting, so the donor decides first and is
            # not contacted before they have agreed to anything.
            "contact": a.request.contact_phone if a.phone_visible else None,
        },
    } for a in qs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answer(request, pk):
    """body: { accept: true|false }"""
    d = Donor.objects.filter(user=request.user).first()
    a = Ask.objects.filter(id=pk, donor=d).select_related("request").first()
    if not a:
        return _err("Not found.", code=status.HTTP_404_NOT_FOUND)
    if a.status != Ask.PENDING:
        return _err("You have already answered this.")
    if not a.request.is_live:
        return _err("That request is closed.")

    accept = bool(request.data.get("accept"))
    with transaction.atomic():
        a.status = Ask.ACCEPTED if accept else Ask.DECLINED
        a.answered_at = timezone.now()
        a.save(update_fields=["status", "answered_at"])

    if accept:
        log.info("Blood contact released: donor=%s request=%s", d.id, a.request_id)
    return Response({"detail": "Thank you. They can now see your number."
                     if accept else "Declined. Your number was not shared."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report(request):
    """body: { ask: <id>, reason: "..." }"""
    reason = str(request.data.get("reason") or "").strip()
    if len(reason) < 10:
        return _err("Tell us briefly what happened.")
    a = Ask.objects.filter(id=request.data.get("ask")).first()
    Report.objects.create(reporter=request.user, ask=a, reason=reason[:2000])
    log.warning("Blood bank report from %s about ask %s", request.user.email,
                a.id if a else None)
    return Response({"detail": "Thank you. We will look into it."},
                    status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats(request):
    live = BloodRequest.objects.filter(status=BloodRequest.OPEN,
                                       expires_at__gt=timezone.now()).count()
    return Response({
        "donors": Donor.objects.filter(is_available=True, is_blocked=False).count(),
        "open_requests": live,
        "cities": Donor.objects.values("city").distinct().count(),
        "groups": GROUPS,
    })


# ---------------------------------------------------------------- location

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def location(request):
    """
    body: { share: true, lat: 31.52, lng: 74.35 }

    Coordinates are rounded to two places before they are stored, so the most
    anyone can learn is roughly which part of a city somebody is in.
    """
    d = Donor.objects.filter(user=request.user).first()
    if not d:
        return _err("Register as a donor first.", code=status.HTTP_404_NOT_FOUND)

    share = bool(request.data.get("share"))
    if not share:
        d.share_location = False
        d.save()
        return Response({"detail": "Location sharing turned off."})

    try:
        lat = float(request.data.get("lat"))
        lng = float(request.data.get("lng"))
    except (TypeError, ValueError):
        return _err("Could not read that location.")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return _err("That location is not valid.")

    d.share_location = True
    d.lat, d.lng = lat, lng
    d.save()
    return Response({"detail": "Location saved.", "lat": d.lat, "lng": d.lng})


# ---------------------------------------------------------------- i donated

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def donated(request):
    """Marks today as the donor's last donation, which hides them for 56 days."""
    d = Donor.objects.filter(user=request.user).first()
    if not d:
        return _err("Register as a donor first.", code=status.HTTP_404_NOT_FOUND)

    when = timezone.localdate()
    if d.last_donation and (when - d.last_donation).days < 14:
        return _err("You recorded a donation on %s. If that is wrong, edit your "
                    "profile instead." % d.last_donation.strftime("%d %b"))

    d.last_donation = when
    d.save(update_fields=["last_donation", "updated_at"])
    return Response({"detail": "Thank you. You are hidden from searches until %s."
                     % d.eligible_from.strftime("%d %b %Y"),
                     "eligible_from": d.eligible_from.isoformat()})


# ---------------------------------------------------------------- directory

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def directory(request):
    """
    Counts by country and city, and by blood group within a city.

    Numbers only. The old build returned the donor rows here, contacts and
    all, which is how a single request walked away with the whole list.
    """
    qs = Donor.objects.filter(is_available=True, is_blocked=False, user__is_active=True)

    city = clean_city(request.GET.get("city"))
    if city:
        rows = (qs.filter(city__iexact=city)
                .values("blood_group").annotate(n=Count("id")).order_by("-n"))
        return Response({"city": city, "groups": [
            {"blood_group": r["blood_group"], "donors": r["n"]} for r in rows]})

    out = {}
    for r in (qs.values("country", "city").annotate(n=Count("id")).order_by("-n")):
        out.setdefault(r["country"] or "Not specified", []).append(
            {"city": r["city"], "donors": r["n"]})

    return Response({"countries": [
        {"country": k, "cities": v[:40], "donors": sum(x["donors"] for x in v)}
        for k, v in sorted(out.items(), key=lambda kv: -sum(x["donors"] for x in kv[1]))
    ]})


# ---------------------------------------------------------------- match

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([SearchThrottle])
def match(request, pk):
    """
    Donors who fit one specific request, nearest first.

    Anyone already asked is marked, so the same donor is not pinged twice.
    Still no contact details - those come from an accepted Ask.
    """
    r = BloodRequest.objects.filter(id=pk, requester=request.user).first()
    if not r:
        return _err("Request not found.", code=status.HTTP_404_NOT_FOUND)

    qs = (Donor.objects.filter(is_available=True, is_blocked=False,
                               user__is_active=True,
                               blood_group__in=r.matching_groups())
          .select_related("user"))

    same_city = qs.filter(city__iexact=r.city)
    others = qs.exclude(city__iexact=r.city)[:40]

    asked = set(Ask.objects.filter(request=r).values_list("donor_id", flat=True))

    ref = same_city.filter(share_location=True).first()
    rlat = ref.lat if ref else None
    rlng = ref.lng if ref else None

    rows = []
    for d in list(same_city[:60]) + list(others):
        if not d.is_eligible:
            continue
        item = donor_public(d)
        item["asked"] = d.id in asked
        item["same_city"] = d.city.lower() == r.city.lower()
        if rlat is not None and d.share_location:
            item["km"] = distance_km(rlat, rlng, d.lat, d.lng)
        rows.append(item)

    rows.sort(key=lambda x: (not x["same_city"],
                             x["km"] if x.get("km") is not None else 9999,
                             not x["is_verified"]))
    return Response({"request": {"id": r.id, "blood_group": r.blood_group,
                                 "city": r.city, "hospital": r.hospital},
                     "matches": rows[:60], "count": len(rows)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([SearchThrottle])
def open_requests(request):
    """
    Requests still looking for blood, from everyone.

    No name, no phone number: those belong to the person who posted, and this
    is a public-facing list. A donor who wants to help can see the need and
    register; the requester still chooses who gets their number.
    """
    BloodRequest.objects.filter(status=BloodRequest.OPEN,
                                expires_at__lt=timezone.now()).update(status=BloodRequest.EXPIRED)

    city = clean_city(request.GET.get("city"))
    qs = BloodRequest.objects.filter(status=BloodRequest.OPEN,
                                     expires_at__gt=timezone.now())
    if city:
        qs = qs.filter(city__iexact=city)

    # Most urgent first, then newest.
    order = {"critical": 0, "urgent": 1, "normal": 2}
    rows = sorted(qs.select_related("requester")[:60],
                  key=lambda r: (order.get(r.urgency, 3), -r.created_at.timestamp()))

    return Response({"requests": [{
        "id": r.id,
        "blood_group": r.blood_group,
        "units": r.units,
        "city": r.city,
        "hospital": r.hospital,
        "urgency": r.urgency,
        "note": r.note[:200],
        "created": r.created_at.strftime("%d %b %H:%M"),
        "mine": r.requester_id == request.user.id,
    } for r in rows], "count": len(rows)})
