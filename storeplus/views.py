"""Store add-ons API (/api/storeplus/).
countries/         list of countries the Store sells in (with currency)
me/                seller: GET / POST country, social links, opening hours, show phone
shop/<slug>/       public: digital shop card data (country, socials, hours, open now, contact)
vcf/<slug>/        public: "Save contact" file for the shop
drop/offers/       supplier: my products and their dropship offer; POST {product, on, price}
drop/catalog/      reseller: products other shops let me sell (Pakistan shops)
drop/add/          reseller: POST {product, price} -> a copy in my shop that the supplier ships
drop/mine/         reseller: my dropship products with cost and profit"""
import re
from datetime import datetime

from django.db.models import Q
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from store.models import Merchant, Product

from .models import DropLink, DropOffer, Extra, Region
from .patch import COUNTRIES, buyer_cc, cc_q, cinfo, shop_cc, valid_cc

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
SOCIAL = {"facebook": "https://www.facebook.com/{}", "instagram": "https://www.instagram.com/{}", "tiktok": "https://www.tiktok.com/@{}",
          "youtube": "https://www.youtube.com/@{}", "x": "https://x.com/{}", "website": "https://{}", "whatsapp": "", "map": ""}
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _int(v):
    try:
        return int(str(v).replace(",", "").strip())
    except Exception:
        return None


def _approved(u):
    return Merchant.objects.filter(user=u, status="approved").first() if u.is_authenticated else None


def _extra(m):
    return Extra.objects.get_or_create(merchant=m)[0]


def _clean_social(d):
    out = {}
    for k, pat in SOCIAL.items():
        v = str((d or {}).get(k) or "").strip()[:200]
        if not v:
            continue
        if k == "map":
            mp = maplink(v)
            if mp:
                out[k] = mp
            continue
        if k == "whatsapp":
            n = re.sub(r"[^\d+]", "", v)
            if len(re.sub(r"\D", "", n)) >= 10:
                out[k] = n
            continue
        if re.match(r"^https?://", v, re.I):
            if re.match(r"^https?://[^\s\"'<>]+$", v, re.I):
                out[k] = v
        else:
            v = v.lstrip("@").strip("/")
            if re.match(r"^[\w.\-/]+$", v):
                out[k] = pat.format(v)
    return out


def _clean_hours(d):
    out = {}
    for k in DAYS:
        v = (d or {}).get(k)
        if isinstance(v, list) and len(v) == 2 and all(HHMM.match(str(x)) for x in v) and v[0] != v[1]:
            out[k] = [str(v[0]), str(v[1])]
        else:
            out[k] = None
    return out


def _open_now(m, hours):
    if not hours or not any(hours.get(k) for k in DAYS):
        return None
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(cinfo(shop_cc(m))["tz"]))
    except Exception:
        return None
    t = now.strftime("%H:%M")
    today, yday = DAYS[now.weekday()], DAYS[(now.weekday() - 1) % 7]
    h, y = hours.get(today), hours.get(yday)
    if y and y[1] < y[0] and t < y[1]:                       # still open from last night
        return {"open": True, "until": y[1]}
    if h:
        if h[0] < h[1] and h[0] <= t < h[1]:
            return {"open": True, "until": h[1]}
        if h[1] < h[0] and t >= h[0]:
            return {"open": True, "until": h[1]}
    for i in range(0, 8):
        dd = DAYS[(now.weekday() + i) % 7]
        x = hours.get(dd)
        if x and (i > 0 or x[0] > t):
            return {"open": False, "opens": x[0], "day": "" if i == 0 else ("tomorrow" if i == 1 else dd)}
    return {"open": False}


@api_view(["GET"])
@permission_classes([AllowAny])
def countries(request):
    return Response({"cc": buyer_cc(request), "countries": [cinfo(c[0]) for c in COUNTRIES]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def me(request):
    m = Merchant.objects.filter(user=request.user).first()
    if not m:
        return _err("Open a shop first.", 404)
    x = _extra(m)
    locked = m.orders.exists()
    if request.method == "POST":
        d = request.data
        cc = valid_cc(d.get("country"))
        if cc and cc != shop_cc(m):
            if locked:
                return _err("Your shop already has orders, so its country cannot change. Contact us if you moved.")
            Region.objects.update_or_create(merchant=m, defaults={"country": cc})
            if cc != "PK":
                Product.objects.filter(merchant=m).update(online=False, cod=True)
                DropLink.objects.filter(product__merchant=m).delete()
        x.social = _clean_social(d.get("social") if isinstance(d.get("social"), dict) else {})
        x.hours = _clean_hours(d.get("hours") if isinstance(d.get("hours"), dict) else {})
        x.show_phone = bool(d.get("show_phone"))
        x.save()
    return Response({"country": shop_cc(m), "locked": locked, "countries": [cinfo(c[0]) for c in COUNTRIES], "social": x.social,
                     "hours": x.hours or {k: None for k in DAYS}, "show_phone": x.show_phone, "slug": m.slug, "status": m.status})


@api_view(["GET"])
@permission_classes([AllowAny])
def shop(request, slug):
    m = Merchant.objects.filter(slug=slug, status="approved").select_related("user").first()
    if not m:
        return _err("Shop not found.", 404)
    x = _extra(m)
    ci = cinfo(shop_cc(m))
    return Response({"name": m.name, "slug": m.slug, "city": m.city, "address": m.address, "about": m.about, "logo": ("/media/" + m.logo) if m.logo else "",
                     "kind": m.kind, "country": ci, "social": x.social, "hours": x.hours, "open": _open_now(m, x.hours),
                     "phone": m.phone if x.show_phone else "", "rating": round(m.rating_sum / m.rating_n, 1) if m.rating_n else None,
                     "ratings": m.rating_n, "products": m.products.filter(active=True, hidden=False).count(),
                     "username": getattr(m.user, "username", "")})


def vcf(request, slug):
    m = Merchant.objects.filter(slug=slug, status="approved").first()
    if not m:
        return HttpResponse("Not found", status=404)
    x = _extra(m)
    e = lambda s: re.sub(r"([,;\\])", r"\\\1", str(s or "")).replace("\n", " ")
    lines = ["BEGIN:VCARD", "VERSION:3.0", "FN:" + e(m.name), "ORG:" + e(m.name)]
    if x.show_phone and m.phone:
        lines.append("TEL;TYPE=WORK,VOICE:" + e(m.phone))
    if x.social.get("whatsapp"):
        lines.append("TEL;TYPE=CELL:" + e(x.social["whatsapp"]))
    lines.append("ADR;TYPE=WORK:;;%s;%s;;;%s" % (e(m.address), e(m.city), e(cinfo(shop_cc(m))["name"])))
    lines.append("URL:https://xpertcreation.com/store#shop-" + m.slug)
    for k in ("website", "facebook", "instagram"):
        if x.social.get(k):
            lines.append("URL:" + e(x.social[k]))
    if m.about:
        lines.append("NOTE:" + e(m.about[:300]))
    lines.append("END:VCARD")
    r = HttpResponse("\r\n".join(lines) + "\r\n", content_type="text/vcard; charset=utf-8")
    r["Content-Disposition"] = 'attachment; filename="%s.vcf"' % m.slug
    return r


# ---------------------------------------------------------------- dropshipping (Pakistan shops)
def _pk_shop(request):
    m = _approved(request.user)
    if not m:
        return None, _err("You need an approved shop.", 403)
    if shop_cc(m) != "PK":
        return None, _err("Dropshipping is for shops in Pakistan for now.", 403)
    return m, None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def drop_offers(request):
    m, e = _pk_shop(request)
    if e:
        return e
    if request.method == "POST":
        d = request.data
        p = Product.objects.filter(pk=_int(d.get("product")) or 0, merchant=m).first()
        if not p:
            return _err("Product not found.", 404)
        if DropLink.objects.filter(product=p).exists():
            return _err("This product is itself from another supplier.")
        on, price = bool(d.get("on")), _int(d.get("price"))
        if on and (not price or price < 1 or price > p.price):
            return _err("Set the reseller price: more than 0 and not above your own price (%s)." % p.price)
        off = DropOffer.objects.filter(product=p).first()
        if off:
            off.on = on
            if price:
                off.price = price
            off.save()
        elif on:
            DropOffer.objects.create(product=p, on=True, price=price)
        from .patch import drop_sync
        drop_sync(DropLink.objects.filter(source=p))
    offers = {o.product_id: o for o in DropOffer.objects.filter(product__merchant=m)}
    mine = set(DropLink.objects.filter(product__merchant=m).values_list("product_id", flat=True))
    out = []
    for p in m.products.filter(hidden=False).order_by("-id")[:300]:
        if p.id in mine:
            continue
        o = offers.get(p.id)
        out.append({"id": p.id, "title": p.title, "price": p.price, "stock": p.stock, "active": p.active, "image": ("/media/" + p.images[0]) if p.images else "",
                    "on": bool(o and o.on), "cost": o.price if o else 0, "resellers": DropLink.objects.filter(source=p).count()})
    return Response({"products": out})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def drop_catalog(request):
    m, e = _pk_shop(request)
    if e:
        return e
    q = str(request.GET.get("q") or "").strip()[:60]
    qs = DropOffer.objects.filter(on=True, product__active=True, product__hidden=False, product__stock__gt=0, product__merchant__status="approved") \
        .filter(cc_q("PK", "product__merchant__")).exclude(product__merchant=m).select_related("product", "product__merchant")
    if q:
        qs = qs.filter(Q(product__title__icontains=q) | Q(product__description__icontains=q) | Q(product__merchant__name__icontains=q))
    have = set(DropLink.objects.filter(product__merchant=m).values_list("source_id", flat=True))
    return Response({"offers": [{"id": o.product_id, "title": o.product.title, "image": ("/media/" + o.product.images[0]) if o.product.images else "",
                                 "cost": o.price, "retail": o.product.price, "stock": o.product.stock, "delivery_fee": o.product.delivery_fee,
                                 "cod": o.product.cod, "supplier": o.product.merchant.name, "city": o.product.merchant.city, "added": o.product_id in have}
                                for o in qs.order_by("-id")[:300]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def drop_add(request):
    m, e = _pk_shop(request)
    if e:
        return e
    from store import views as sv
    d = request.data
    off = DropOffer.objects.filter(product_id=_int(d.get("product")) or 0, on=True).select_related("product", "product__merchant").first()
    if not off or off.product.merchant_id == m.id or off.product.merchant.status != "approved" or shop_cc(off.product.merchant) != "PK":
        return _err("This product is not open for dropshipping.", 404)
    if DropLink.objects.filter(product__merchant=m, source=off.product).exists():
        return _err("It is already in your shop.")
    price = _int(d.get("price"))
    if not price or price < off.price:
        return _err("Your price must be at least the supplier price (Rs %s)." % "{:,}".format(off.price))
    t = sv.tier(m)
    if m.products.filter(active=True).count() >= sv.TIERS[t]["limit"]:
        return _err("Your %s plan allows %d live products. Upgrade your plan or pause a product." % (sv.TIERS[t]["name"], sv.TIERS[t]["limit"]), 403)
    s = off.product
    p = Product.objects.create(merchant=m, title=s.title, category=s.category, description=s.description, price=price, stock=s.stock,
                               images=list(s.images or []), cod=s.cod, online=s.online, delivery_fee=s.delivery_fee, delivery_days=s.delivery_days, active=True)
    DropLink.objects.create(product=p, source=s, supplier=s.merchant)
    try:
        from notifications.views import notify
        notify(s.merchant.user, "store", "%s added your product %s to their shop (dropship)" % (m.name, s.title[:50]), "/store#seller-drop")
    except Exception:
        pass
    return Response({"ok": True, "id": p.id})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def drop_mine(request):
    m, e = _pk_shop(request)
    if e:
        return e
    out = []
    for lk in DropLink.objects.filter(product__merchant=m).select_related("product", "source", "supplier").order_by("-id")[:300]:
        off = DropOffer.objects.filter(product=lk.source).first() if lk.source else None
        cost = off.price if off else 0
        p = lk.product
        out.append({"id": p.id, "title": p.title, "price": p.price, "cost": cost, "profit": p.price - cost, "stock": p.stock, "active": p.active,
                    "available": bool(off and off.on and lk.source and lk.source.active), "supplier": lk.supplier.name, "sold": p.sold,
                    "image": ("/media/" + p.images[0]) if p.images else ""})
    return Response({"products": out})


# ---- setup_qr_v1: an exact location pin (Google Maps link or "lat,lng" from "Use my location")
def maplink(v):
    import re as _re9
    v = str(v or "").strip()[:300]
    m = _re9.match(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$", v)
    if m and abs(float(m.group(1))) <= 90 and abs(float(m.group(2))) <= 180:
        return "https://www.google.com/maps?q=%s,%s" % (m.group(1), m.group(2))
    if _re9.match(r"^https://(www\.)?(google\.[a-z.]+/maps|maps\.google\.[a-z.]+|maps\.app\.goo\.gl|goo\.gl/maps)[^\s\"'<>]*$", v, _re9.I):
        return v
    return ""
