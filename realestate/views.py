"""Property listings API (/api/property/)."""
import os
import re
import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import KINDS, PURPOSE, UNITS, Listing, Report

LIVE_DAYS = 60
MAX_PICS, MAX_PIC_MB = 8, 8
MAX_ACTIVE = 20                    # active listings per member (agents: 100)
CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Gujranwala", "Sialkot", "Quetta",
          "Hyderabad", "Bahawalpur", "Sargodha", "Abbottabad", "Sahiwal", "Gujrat", "Okara", "Sheikhupura", "Murree", "Other"]
KD, PD, UD = dict(KINDS), dict(PURPOSE), dict(UNITS)


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _kyc(u):
    k = getattr(u, "person_kyc", None)
    try:
        return bool(k and k.status == "approved")
    except Exception:
        return False


def _txt(v, n):
    return re.sub(r"[ \t]+", " ", str(v or "")).replace("\r\n", "\n").strip()[:n]


def _int(v, lo, hi):
    try:
        v = int(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _avatar(u):
    try:
        from accounts.views import avatar_url
        return avatar_url(getattr(u, "avatar", "")) or ""
    except Exception:
        return ""


def _expire():
    Listing.objects.filter(status="active", renewed_at__lt=timezone.now() - timedelta(days=LIVE_DAYS)).update(status="expired")


def _out(l, viewer, full=False):
    u = l.owner
    d = {"id": l.id, "purpose": l.purpose, "purpose_name": PD.get(l.purpose), "kind": l.kind, "kind_name": KD.get(l.kind), "title": l.title,
         "price": l.price, "city": l.city, "locality": l.locality, "size": float(l.size), "unit": l.unit, "unit_name": UD.get(l.unit),
         "bedrooms": l.bedrooms, "bathrooms": l.bathrooms, "furnished": l.furnished, "by_agent": l.by_agent,
         "images": ["/media/" + p for p in (l.images or [])], "status": l.status, "when": l.renewed_at.isoformat(), "views": l.views,
         "verified": _kyc(u), "mine": bool(viewer.is_authenticated and viewer.pk == l.owner_id),
         "owner": {"id": u.pk, "name": (getattr(u, "full_name", "") or u.username or "Member")[:60], "username": u.username or "", "avatar": _avatar(u)}}
    if full:
        d["description"] = l.description
        d["expires"] = (l.renewed_at + timedelta(days=LIVE_DAYS)).isoformat()
        d["phone"] = l.phone if viewer.is_authenticated else ""          # signed-in members only (keeps scrapers out)
        d["phone_hidden"] = not viewer.is_authenticated
        d["more"] = [_out(x, viewer) for x in Listing.objects.filter(city=l.city, purpose=l.purpose, status="active", hidden=False)
                     .exclude(pk=l.pk).select_related("owner").order_by("-renewed_at")[:4]]
    return d


@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    _expire()
    u = request.user
    by_city = dict(Listing.objects.filter(status="active", hidden=False).values_list("city").annotate(n=Count("id")))
    return Response({"purposes": PURPOSE, "kinds": KINDS, "units": UNITS, "cities": CITIES, "counts": by_city,
                     "me": ({"id": u.pk, "kyc": _kyc(u), "staff": _staff(u), "phone": getattr(u, "whatsapp", "") or getattr(u, "phone", "") or ""}
                            if u.is_authenticated else None)})


def _save(request, l):
    d, u = request.data, request.user
    title, desc = _txt(d.get("title"), 120), _txt(d.get("description"), 5000)
    price = _int(d.get("price"), 1000, 100000000000)
    city, loc = _txt(d.get("city"), 60), _txt(d.get("locality"), 120)
    try:
        size = Decimal(str(d.get("size") or "0").replace(",", ""))
    except InvalidOperation:
        size = Decimal(0)
    phone = re.sub(r"[^\d+]", "", str(d.get("phone") or ""))[:20]
    if len(title) < 10 or len(desc) < 20:
        return _err("Give a clear title (10+ letters) and describe the property (20+ letters).")
    if price is None:
        return _err("Enter the price in rupees (for rent: per month).")
    if not city or len(loc) < 3:
        return _err("Choose the city and write the area or society (e.g. DHA Phase 6, Block C).")
    if not (Decimal("0.1") <= size <= Decimal("100000")):
        return _err("Enter the size, e.g. 5 (marla) or 1 (kanal).")
    if len(re.sub(r"\D", "", phone)) < 10:
        return _err("Enter a phone or WhatsApp number buyers can call (e.g. 03001234567).")
    by_agent = bool(d.get("by_agent"))
    if by_agent and not _kyc(u):
        return _err("Agents and dealers need a verified ID first. Get verified, or post as the owner.", 403)
    l.purpose = d.get("purpose") if d.get("purpose") in PD else "sale"
    l.kind = d.get("kind") if d.get("kind") in KD else "house"
    l.unit = d.get("unit") if d.get("unit") in UD else "marla"
    l.title, l.description, l.price, l.city, l.locality, l.size, l.phone, l.by_agent = title, desc, price, city, loc, size, phone, by_agent
    l.bedrooms = _int(d.get("bedrooms"), 0, 50) or 0
    l.bathrooms = _int(d.get("bathrooms"), 0, 50) or 0
    l.furnished = bool(d.get("furnished"))
    l.save()
    return Response(_out(l, u, True))


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def listings(request):
    u = request.user
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in first.", 401)
        if not getattr(u, "is_email_verified", True):
            return _err("Verify your email before posting a property.", 403)
        cap = 100 if _kyc(u) else MAX_ACTIVE
        if Listing.objects.filter(owner=u, status="active").count() >= cap:
            return _err("You have %d active listings. Mark some as sold or rented first." % cap)
        return _save(request, Listing(owner=u))
    _expire()
    g = request.GET
    qs = Listing.objects.filter(hidden=False).select_related("owner")
    if g.get("mine") and u.is_authenticated:
        qs = qs.filter(owner=u)
    else:
        qs = qs.filter(status="active")
    if g.get("purpose") in PD:
        qs = qs.filter(purpose=g["purpose"])
    if g.get("kind") in KD:
        qs = qs.filter(kind=g["kind"])
    if g.get("city"):
        qs = qs.filter(city__iexact=g["city"][:60])
    q = _txt(g.get("q"), 60)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(locality__icontains=q) | Q(description__icontains=q))
    lo, hi = _int(g.get("min"), 0, 10 ** 11), _int(g.get("max"), 0, 10 ** 11)
    if lo:
        qs = qs.filter(price__gte=lo)
    if hi:
        qs = qs.filter(price__lte=hi)
    beds = _int(g.get("beds"), 1, 20)
    if beds:
        qs = qs.filter(bedrooms__gte=beds)
    if g.get("verified"):
        ids = [x.pk for x in qs[:500] if _kyc(x.owner)]
        qs = qs.filter(pk__in=ids)
    sort = {"low": ["price"], "high": ["-price"], "views": ["-views"]}.get(g.get("sort"), ["-renewed_at", "-id"])
    from market.views import featured_ids
    fid = featured_ids("property_boost")
    if fid and not g.get("mine"):
        from django.db.models import Case, IntegerField, Value, When
        qs = qs.annotate(fx=Case(When(pk__in=list(fid), then=Value(1)), default=Value(0), output_field=IntegerField()))
        sort = ["-fx"] + sort
    qs = qs.order_by(*sort)
    page = _int(g.get("page"), 1, 500) or 1
    total = qs.count()
    return Response({"total": total, "page": page, "pages": (total + 23) // 24, "listings": [dict(_out(l, u), featured=l.id in fid) for l in qs[(page - 1) * 24: page * 24]]})


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
def listing(request, pk):
    l = Listing.objects.select_related("owner").filter(pk=pk).first()
    u = request.user
    if not l or (l.hidden and not (_staff(u) or (u.is_authenticated and u.pk == l.owner_id))):
        return _err("This property is not available.", 404)
    if request.method in ("POST", "DELETE"):
        if not u.is_authenticated or u.pk != l.owner_id:
            return _err("Only the owner can change this listing.", 403)
        if request.method == "DELETE":
            for p in l.images or []:
                try:
                    os.remove(os.path.join(str(settings.MEDIA_ROOT), p))
                except OSError:
                    pass
            l.delete()
            return Response({"ok": True})
        return _save(request, l)
    if not (u.is_authenticated and u.pk == l.owner_id):
        Listing.objects.filter(pk=l.pk).update(views=F("views") + 1)
    from market.views import featured_ids
    return Response(dict(_out(l, u, True), featured=l.id in featured_ids("property_boost")))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def act(request, pk, act):
    u = request.user
    l = Listing.objects.select_related("owner").filter(pk=pk).first()
    if not l:
        return _err("Not found.", 404)
    if act in ("sold", "rented", "renew", "active"):
        if u.pk != l.owner_id:
            return _err("Only the owner can do that.", 403)
        if act == "renew" or act == "active":
            l.status, l.renewed_at = "active", timezone.now()
        else:
            l.status = act
        l.save(update_fields=["status", "renewed_at"])
    elif act == "report":
        reason = _txt(request.data.get("reason"), 300)
        if len(reason) < 5:
            return _err("Tell us what is wrong (fake, already sold, wrong price, asks for advance money...).")
        try:
            Report.objects.create(listing=l, user=u, reason=reason)
        except IntegrityError:
            return _err("You already reported this listing. Our team will check it.")
        l.reports = l.report_rows.count()
        if l.reports >= 3:
            l.hidden = True                                       # three different members: hide until the team checks
        l.save(update_fields=["reports", "hidden"])
        try:
            from notifications.views import notify_admins
            notify_admins("property", "Property listing reported (%d): %s" % (l.reports, l.title[:60]), "/market#prop-%d" % l.id)
        except Exception:
            pass
        return Response({"ok": True})
    elif act in ("hide", "unhide"):
        if not _staff(u):
            return _err("Team only.", 403)
        l.hidden = act == "hide"
        l.save(update_fields=["hidden"])
    else:
        return _err("Unknown action.")
    return Response(_out(l, u, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def image(request, pk):
    l = Listing.objects.filter(pk=pk, owner=request.user).first()
    if not l:
        return _err("Only the owner can change the photos.", 403)
    pics = list(l.images or [])
    if request.data.get("remove") is not None:
        i = _int(request.data.get("remove"), 0, 20)
        if i is not None and i < len(pics):
            old = pics.pop(i)
            try:
                os.remove(os.path.join(str(settings.MEDIA_ROOT), old))
            except OSError:
                pass
    elif request.data.get("first") is not None:
        i = _int(request.data.get("first"), 0, 20)
        if i is not None and i < len(pics):
            pics.insert(0, pics.pop(i))
    else:
        f = request.FILES.get("file")
        if not f:
            return _err("Choose a photo.")
        if len(pics) >= MAX_PICS:
            return _err("A listing can have %d photos." % MAX_PICS)
        if f.size > MAX_PIC_MB * 1024 * 1024:
            return _err("The photo is over %d MB." % MAX_PIC_MB)
        from PIL import Image, ImageOps
        try:
            im = Image.open(f); im.load()
        except Exception:
            return _err("That file is not a photo we can read.")
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, (1200, 900), Image.LANCZOS)
        rel = os.path.join("property", timezone.localdate().strftime("%Y%m"), "%d_%s.webp" % (l.id, secrets.token_hex(6)))
        full = os.path.join(str(settings.MEDIA_ROOT), rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        im.save(full, "WEBP", quality=80)
        pics.append(rel)
    l.images = pics
    l.save(update_fields=["images"])
    return Response(_out(l, request.user, True))
