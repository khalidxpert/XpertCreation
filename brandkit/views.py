"""Brand kit API (/api/brand/).
kit/         GET / POST: my logo design, business details, and the logo PNG made in the logo maker.
work/<uid>/  public: a member's shop, services and properties (shown on their XpertConnect profile).
shop/<slug>/ public: everything the shop landing page (/shop/<slug>) needs: shop, products, brand colours, contact."""
import os
import re
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import BrandKit

User = get_user_model()
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _media(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p else ""


def _name(u):
    return (getattr(u, "full_name", "") or getattr(u, "username", "") or "Member").strip()


def _merchant(u):
    try:
        from store.models import Merchant
        return Merchant.objects.filter(user=u).first()
    except Exception:
        return None


def _clean_data(d):
    """Only known keys, short strings, colours as #rrggbb."""
    if not isinstance(d, dict):
        return {}
    out = {}
    for k in ("icon", "layout", "font", "shape", "initials"):
        if k in d:
            out[k] = _txt(d.get(k), 24)
    for k in ("c1", "c2", "c3", "bg"):
        if HEX.match(str(d.get(k, ""))):
            out[k] = d[k]
    for k, n in (("phone", 24), ("email", 80), ("web", 80), ("address", 160), ("city", 60), ("person", 60), ("role", 60)):
        if k in d:
            out[k] = _txt(d.get(k), n)
    return out


def _kit_out(k, u):
    m = _merchant(u)
    d = dict(k.data or {}) if k else {}
    return {"name": (k.name if k and k.name else (m.name if m else _name(u))), "tagline": k.tagline if k else "",
            "data": d, "logo": _media(k.logo) if k else "", "updated": k.updated_at.isoformat() if k else "",
            "defaults": {"phone": (m.phone if m else "") or getattr(u, "phone", "") or "", "email": u.email or "",
                         "city": (m.city if m else ""), "address": (m.address if m else ""), "person": _name(u)},
            "shop": {"name": m.name, "slug": m.slug, "status": m.status, "logo": _media(m.logo)} if m else None,
            "username": getattr(u, "username", "") or ""}


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def kit(request):
    u = request.user
    k = BrandKit.objects.filter(user=u).first()
    if request.method == "GET":
        return Response(_kit_out(k, u))
    d = request.data
    k = k or BrandKit(user=u)
    if "name" in d:
        k.name = _txt(d.get("name"), 60)
    if "tagline" in d:
        k.tagline = _txt(d.get("tagline"), 80)
    if "data" in d:
        raw = d.get("data")
        if isinstance(raw, str):
            import json
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = {}
        k.data = _clean_data(raw)
    f = request.FILES.get("logo")
    if f:
        if f.size > 3 * 1024 * 1024:
            return _err("The logo file is too big.")
        from PIL import Image
        try:
            im = Image.open(f); im.load()
        except Exception:
            return _err("That is not a picture.")
        im = im.convert("RGBA"); im.thumbnail((1200, 1200), Image.LANCZOS)
        rel = os.path.join("brand", str(u.id), secrets.token_hex(8) + ".png")
        full = os.path.join(str(settings.MEDIA_ROOT), rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        im.save(full, "PNG", optimize=True)
        if k.logo and k.logo.startswith("brand/"):
            try:
                os.remove(os.path.join(str(settings.MEDIA_ROOT), k.logo))
            except OSError:
                pass
        k.logo = rel
        if d.get("use_for_shop") in ("1", "true", True):
            m = _merchant(u)
            if m:
                sq = Image.new("RGBA", (400, 400), (255, 255, 255, 255))
                src = im
                mf = request.FILES.get("mark")          # the square symbol reads better in a small shop logo
                if mf and mf.size < 3 * 1024 * 1024:
                    try:
                        src = Image.open(mf).convert("RGBA")
                    except Exception:
                        src = im
                t = src.copy(); t.thumbnail((360, 360), Image.LANCZOS)
                sq.paste(t, ((400 - t.width) // 2, (400 - t.height) // 2), t)
                srel = os.path.join("store", "logo", "%d_%s.webp" % (m.id, secrets.token_hex(6)))
                sfull = os.path.join(str(settings.MEDIA_ROOT), srel)
                os.makedirs(os.path.dirname(sfull), exist_ok=True)
                sq.convert("RGB").save(sfull, "WEBP", quality=88)
                m.logo = srel; m.save(update_fields=["logo"])
    k.save()
    return Response(_kit_out(k, u))


def _slug(u):
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).exclude(visibility=ProProfile.HIDDEN).first()
        return p.slug if p else ""
    except Exception:
        return ""


def _work(u):
    out = {"shop": None, "gigs": [], "properties": [], "username": getattr(u, "username", "") or ""}
    m = _merchant(u)
    if m and m.status == "approved":
        out["shop"] = {"name": m.name, "slug": m.slug, "city": m.city, "logo": _media(m.logo), "about": (m.about or "")[:160],
                       "products": m.products.filter(active=True, hidden=False).count()}
    try:
        from market.models import Gig
        for g in Gig.objects.filter(seller=u, active=True, hidden=False).order_by("-orders_done", "-id")[:6]:
            out["gigs"].append({"id": g.id, "title": g.title, "price": g.price, "image": _media((g.images or [""])[0]),
                                "rating": round(g.rating_sum / g.rating_n, 1) if g.rating_n else None})
    except Exception:
        pass
    try:
        from realestate.models import Listing
        for l in Listing.objects.filter(owner=u, status="active", hidden=False).order_by("-renewed_at")[:6]:
            out["properties"].append({"id": l.id, "title": l.title, "price": l.price, "city": l.city, "purpose": l.purpose,
                                      "image": _media((l.images or [""])[0])})
    except Exception:
        pass
    return out


@api_view(["GET"])
@permission_classes([AllowAny])
def work(request, uid):
    u = User.objects.filter(pk=uid, is_active=True).first()
    if not u or getattr(u, "is_blocked", False):
        return _err("Not found.", 404)
    return Response(_work(u))


@api_view(["GET"])
@permission_classes([AllowAny])
def shop(request, slug):
    try:
        from store.models import Merchant
        from store.views import _m, _p, _public
    except Exception:
        return _err("The Store is not available.", 404)
    m = Merchant.objects.filter(slug=slug[:90], status="approved").select_related("user").first()
    if not m:
        return _err("Shop not found.", 404)
    k = BrandKit.objects.filter(user=m.user).first()
    d = k.data if k else {}
    signed = request.user.is_authenticated
    w = _work(m.user)
    return Response({"shop": _m(m, True), "address": m.address, "phone": m.phone if signed else "", "phone_hidden": not signed,
                     "products": [_p(p) for p in _public().filter(merchant=m).order_by("-sold", "-id")[:60]],
                     "brand": {"tagline": k.tagline if k else "", "logo": _media(k.logo) if k else "",
                               "c1": d.get("c1", "#1B4DFF"), "c2": d.get("c2", "#7C3AED")},
                     "owner": {"name": _name(m.user), "username": getattr(m.user, "username", "") or "", "slug": _slug(m.user)},
                     "gigs": w["gigs"], "properties": w["properties"]})
