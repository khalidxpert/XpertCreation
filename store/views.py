"""XpertCreation Store API (/api/store/). See models.py."""
import os
import re
import secrets
import urllib.parse
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CATS, Merchant, Order, Product, Quote, Review, StockMove

TIERS = {"bronze": {"name": "Bronze", "limit": 10, "price": 0}, "gold": {"name": "Gold", "limit": 100, "price": 1999},
         "platinum": {"name": "Platinum", "limit": 1000, "price": 4999}}
FEE_PCT = 5                    # XpertCreation keeps 5% of online-paid orders (cash on delivery: no fee)
AUTO_DONE_DAYS = 3             # online order completes this long after "delivered" if the buyer says nothing
MAX_PICS = 6
SITE = "https://xpertcreation.com"
CK = dict(CATS)
COURIERS = ["TCS", "Leopards", "M&P", "Trax", "PostEx", "Call Courier", "BlueEX", "Pakistan Post", "Rider", "Own delivery", "Other"]


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


def _phone(v):
    p = re.sub(r"[^\d+]", "", str(v or ""))[:20]
    return p if len(re.sub(r"\D", "", p)) >= 10 else ""


def _notify(user, text, link):
    try:
        from notifications.views import notify
        notify(user, "store", text, link)
    except Exception:
        pass


def _admins(text, link="/store#team"):
    try:
        from notifications.views import notify_admins
        notify_admins("store", text, link)
    except Exception:
        pass


def _shop():
    from shop import views as sv
    return sv


def _mode():
    try:
        return _shop().setting().mode
    except Exception:
        return "off"


def _can_pay_online(u):
    m = _mode()
    return m == "live" or (m == "test" and _staff(u))


# ---------------------------------------------------------------- tiers
def tier(m):
    """Highest tier with a paid, running Gold/Platinum order on the Promote page; Bronze otherwise."""
    try:
        from shop.models import Order as SO
        now = timezone.now()
        run = set(SO.objects.filter(product__in=("merchant_gold", "merchant_platinum"), status="paid", target_id=m.id,
                                    starts_at__lte=now, ends_at__gt=now).values_list("product", flat=True))
    except Exception:
        run = set()
    return "platinum" if "merchant_platinum" in run else "gold" if "merchant_gold" in run else "bronze"


def _until(m):
    try:
        from shop.models import Order as SO
        o = SO.objects.filter(product__in=("merchant_gold", "merchant_platinum"), status="paid", target_id=m.id,
                              ends_at__gt=timezone.now()).order_by("-ends_at").first()
        return o.ends_at.isoformat() if o else ""
    except Exception:
        return ""


def enforce(m):
    """If a shop has more live products than its tier allows (e.g. Gold ran out), pause the newest extras."""
    lim = TIERS[tier(m)]["limit"]
    live = list(m.products.filter(active=True).order_by("id").values_list("id", flat=True))
    if len(live) > lim:
        Product.objects.filter(id__in=live[lim:]).update(active=False)
        return len(live) - lim
    return 0


def _enforce_all():
    if cache.get("store:enforce"):
        return
    cache.set("store:enforce", 1, 3600)
    for m in Merchant.objects.filter(status="approved"):
        enforce(m)


# ---------------------------------------------------------------- output
def _avatar(u):
    try:
        from accounts.views import avatar_url
        return avatar_url(getattr(u, "avatar", "")) or ""
    except Exception:
        return ""


def _m(m, full=False):
    t = tier(m)
    d = {"id": m.id, "name": m.name, "slug": m.slug, "city": m.city, "kind": m.kind, "tier": t, "tier_name": TIERS[t]["name"],
         "logo": ("/media/" + m.logo) if m.logo else "", "rating": round(m.rating_sum / m.rating_n, 1) if m.rating_n else None,
         "ratings": m.rating_n, "verified": _kyc(m.user)}
    if full:
        d.update({"about": m.about, "since": m.created_at.isoformat(), "products": m.products.filter(active=True, hidden=False).count(),
                  "sold": m.products.aggregate(s=Sum("sold"))["s"] or 0})
    return d


def _p(p, full=False):
    d = {"id": p.id, "title": p.title, "category": p.category, "cat": CK.get(p.category, ""), "price": p.price, "old_price": p.old_price,
         "off": int(round((p.old_price - p.price) * 100 / p.old_price)) if p.old_price > p.price else 0,
         "images": ["/media/" + x for x in (p.images or [])], "cod": p.cod, "online": p.online, "stock": p.stock,
         "wholesale": p.wholesale_price if (p.wholesale_price and p.moq) else 0, "moq": p.moq if p.wholesale_price else 0,
         "rating": round(p.rating_sum / p.rating_n, 1) if p.rating_n else None, "ratings": p.rating_n, "sold": p.sold,
         "delivery_fee": p.delivery_fee, "delivery_days": p.delivery_days, "active": p.active and not p.hidden,
         "merchant": {"id": p.merchant_id, "name": p.merchant.name, "slug": p.merchant.slug, "city": p.merchant.city, "tier": tier(p.merchant)}}
    if full:
        d["description"] = p.description
        d["shop"] = _m(p.merchant, True)
        rv = Review.objects.filter(product=p).select_related("buyer")
        stars = {n: 0 for n in range(1, 6)}
        for r in rv.values("rating").annotate(n=Count("id")):
            stars[r["rating"]] = r["n"]
        d["stars"] = stars
        d["reviews"] = [{"id": r.id, "rating": r.rating, "text": r.text, "reply": r.reply, "when": r.created_at.isoformat(),
                         "by": ((getattr(r.buyer, "full_name", "") or r.buyer.username or "Buyer").split(" ")[0])[:30]} for r in rv[:40]]
        d["more"] = [_p(x) for x in _public().filter(merchant_id=p.merchant_id).exclude(pk=p.pk)[:6]]
        d["similar"] = [_p(x) for x in _public().filter(category=p.category).exclude(merchant_id=p.merchant_id)[:6]]
    return d


def _public():
    return Product.objects.filter(active=True, hidden=False, merchant__status="approved", stock__gt=0).select_related("merchant")


# ---------------------------------------------------------------- browse
@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    _enforce_all()
    u = request.user
    me = None
    if u.is_authenticated:
        m = getattr(u, "merchant", None) if hasattr(u, "merchant") else None
        try:
            m = Merchant.objects.filter(user=u).first()
        except Exception:
            m = None
        me = {"id": u.pk, "name": (getattr(u, "full_name", "") or u.username), "kyc": _kyc(u), "staff": _staff(u), "can_pay_online": _can_pay_online(u),
              "phone": getattr(u, "whatsapp", "") or getattr(u, "phone", "") or "",
              "merchant": ({"id": m.id, "status": m.status, "name": m.name, "slug": m.slug} if m else None)}
    return Response({"cats": CATS, "tiers": TIERS, "fee_pct": FEE_PCT, "couriers": COURIERS, "mode": _mode(), "me": me})


@api_view(["GET"])
@permission_classes([AllowAny])
def home(request):
    pub = _public()
    flash = sorted([p for p in pub.filter(old_price__gt=F("price")).order_by("-id")[:60]], key=lambda p: -(p.old_price - p.price) / p.old_price)[:12]
    plat = [m for m in Merchant.objects.filter(status="approved").order_by("-id")[:200] if tier(m) == "platinum"][:10]
    counts = dict(pub.values_list("category").annotate(n=Count("id")))
    fid = _featured()
    return Response({"featured": [dict(_p(p), featured=True) for p in pub.filter(pk__in=list(fid))[:12]], "flash": [_p(p) for p in flash], "top": [_p(p) for p in pub.order_by("-sold", "-id")[:12]],
                     "new": [_p(p) for p in pub.order_by("-id")[:24]], "b2b": [_p(p) for p in pub.filter(wholesale_price__gt=0, moq__gt=0)[:12]],
                     "shops": [_m(m) for m in plat], "counts": counts})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def products(request):
    u = request.user
    if request.method == "POST":
        m = _my_merchant(u)
        if not m or m.status != "approved":
            return _err("Only approved merchants can add products.", 403)
        t = tier(m)
        if m.products.filter(active=True).count() >= TIERS[t]["limit"]:
            return _err("Your %s plan allows %d live products. Upgrade your plan or pause a product." % (TIERS[t]["name"], TIERS[t]["limit"]), 403)
        return _save_p(request, Product(merchant=m))
    g = request.GET
    if g.get("mine"):
        m = _my_merchant(u)
        if not m:
            return Response({"products": []})
        enforce(m)
        return Response({"products": [_p(p) for p in m.products.select_related("merchant").order_by("-id")[:500]]})
    qs = _public()
    if g.get("cat") in CK:
        qs = qs.filter(category=g["cat"])
    if g.get("shop"):
        qs = qs.filter(merchant__slug=g["shop"][:90])
    q = _txt(g.get("q"), 60)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(merchant__name__icontains=q))
    lo, hi = _int(g.get("min"), 0, 10 ** 9), _int(g.get("max"), 0, 10 ** 9)
    if lo:
        qs = qs.filter(price__gte=lo)
    if hi:
        qs = qs.filter(price__lte=hi)
    if g.get("b2b"):
        qs = qs.filter(wholesale_price__gt=0, moq__gt=0)
    if g.get("cod"):
        qs = qs.filter(cod=True)
    if g.get("deal"):
        qs = qs.filter(old_price__gt=F("price"))
    sort = {"low": ["price"], "high": ["-price"], "new": ["-id"], "rated": ["-rating_sum", "-id"]}.get(g.get("sort"), ["-sold", "-id"])
    fid = _featured()
    if fid:
        from django.db.models import Case, IntegerField, Value, When
        qs = qs.annotate(fx=Case(When(pk__in=list(fid), then=Value(1)), default=Value(0), output_field=IntegerField()))
        sort = ["-fx"] + sort
    qs = qs.order_by(*sort)
    page = _int(g.get("page"), 1, 500) or 1
    total = qs.count()
    return Response({"total": total, "page": page, "pages": (total + 39) // 40, "products": [dict(_p(p), featured=p.id in fid) for p in qs[(page - 1) * 40: page * 40]]})


def _featured():
    try:
        from shop.models import Order as SO
        now = timezone.now()
        return set(SO.objects.filter(product="product_boost", status="paid", starts_at__lte=now, ends_at__gt=now).values_list("target_id", flat=True))
    except Exception:
        return set()


def _save_p(request, p):
    d = request.data
    title, desc = _txt(d.get("title"), 150), _txt(d.get("description"), 6000)
    price, old = _int(d.get("price"), 10, 10 ** 8), _int(d.get("old_price") or 0, 0, 10 ** 8)
    stock, fee, days = _int(d.get("stock"), 0, 10 ** 6), _int(d.get("delivery_fee") or 0, 0, 100000), _int(d.get("delivery_days") or 3, 1, 60)
    wp, moq = _int(d.get("wholesale_price") or 0, 0, 10 ** 8), _int(d.get("moq") or 0, 0, 10 ** 7)
    if len(title) < 8 or len(desc) < 20:
        return _err("Give a clear product name (8+ letters) and a description (20+ letters).")
    if None in (price, old, stock, fee, days, wp, moq):
        return _err("Check the numbers: price, old price, stock, delivery fee and days.")
    if old and old <= price:
        return _err("The old (crossed-out) price must be higher than the price, or leave it empty.")
    if wp and (wp >= price or moq < 2):
        return _err("Wholesale price must be lower than the retail price, with a minimum order of 2 or more.")
    cod, online = bool(d.get("cod", True)), bool(d.get("online"))
    if not cod and not online:
        return _err("Choose cash on delivery, online payment, or both.")
    cost, rl = _int(d.get("cost_price") or 0, 0, 10 ** 8), _int(d.get("reorder_level") or 0, 0, 10 ** 6)
    if cost is None or rl is None:
        return _err("Check the cost price and reorder level.")
    new = not p.pk
    diff = stock - (p.stock if p.pk else 0)
    p.title, p.description, p.price, p.old_price, p.stock = title, desc, price, old, stock
    p.sku, p.cost_price, p.reorder_level = _txt(d.get("sku"), 40), cost, rl
    p.delivery_fee, p.delivery_days, p.wholesale_price, p.moq, p.cod, p.online = fee, days, wp, moq if wp else 0, cod, online
    p.category = d.get("category") if d.get("category") in CK else "other"
    if "active" in d:
        want = bool(d.get("active"))
        if want and not p.active and p.pk:
            t = tier(p.merchant)
            if p.merchant.products.filter(active=True).count() >= TIERS[t]["limit"]:
                return _err("Your %s plan allows %d live products. Upgrade to put more live." % (TIERS[t]["name"], TIERS[t]["limit"]), 403)
        p.active = want
    p.save()
    if diff:
        StockMove.objects.create(product=p, kind="opening" if new else "adjust", qty=diff, unit=cost, note="Opening stock" if new else "Stock changed on the product form")
    d = _p(p, True); d.update(_inv(p)); d["mine"] = True
    return Response(d)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
def product(request, pk):
    p = Product.objects.select_related("merchant", "merchant__user").filter(pk=pk).first()
    u = request.user
    own = bool(p and u.is_authenticated and p.merchant.user_id == u.pk)
    if not p or ((p.hidden or p.merchant.status != "approved") and not (own or _staff(u))):
        return _err("This product is not available.", 404)
    if request.method in ("POST", "DELETE"):
        if not own:
            return _err("Only the shop owner can change this product.", 403)
        if request.method == "DELETE":
            if Order.objects.filter(merchant=p.merchant, status__in=("placed", "pending", "confirmed", "shipped")).exists() and p.sold:
                p.active = False; p.save(update_fields=["active"])
                return Response({"ok": True, "paused": True})
            for x in p.images or []:
                try:
                    os.remove(os.path.join(str(settings.MEDIA_ROOT), x))
                except OSError:
                    pass
            p.delete()
            return Response({"ok": True})
        return _save_p(request, p)
    if not own:
        Product.objects.filter(pk=p.pk).update(views=F("views") + 1)
    d = _p(p, True); d["mine"] = own
    if own:
        d.update(_inv(p))
    return Response(d)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def product_image(request, pk):
    p = Product.objects.filter(pk=pk, merchant__user=request.user).first()
    if not p:
        return _err("Only the shop owner can change the photos.", 403)
    pics = list(p.images or [])
    if request.data.get("remove") is not None:
        i = _int(request.data.get("remove"), 0, 20)
        if i is not None and i < len(pics):
            try:
                os.remove(os.path.join(str(settings.MEDIA_ROOT), pics.pop(i)))
            except OSError:
                pass
    elif request.data.get("first") is not None:
        i = _int(request.data.get("first"), 0, 20)
        if i is not None and i < len(pics):
            pics.insert(0, pics.pop(i))
    else:
        rel = _save_pic(request.FILES.get("file"), "store/p", p.id, (1000, 1000), len(pics) >= MAX_PICS)
        if isinstance(rel, Response):
            return rel
        pics.append(rel)
    p.images = pics; p.save(update_fields=["images"])
    return Response(_p(p, True))


def _save_pic(f, folder, oid, size, full):
    if full:
        return _err("A product can have %d photos." % MAX_PICS)
    if not f:
        return _err("Choose a photo.")
    if f.size > 8 * 1024 * 1024:
        return _err("The photo is over 8 MB.")
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); im.load()
    except Exception:
        return _err("That file is not a photo we can read.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im = ImageOps.pad(im, size, color=(255, 255, 255), method=Image.LANCZOS)   # whole product visible on white, like a shop
    rel = os.path.join(folder, timezone.localdate().strftime("%Y%m"), "%d_%s.webp" % (oid, secrets.token_hex(6)))
    full_p = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full_p), exist_ok=True)
    im.save(full_p, "WEBP", quality=82)
    return rel


@api_view(["GET"])
@permission_classes([AllowAny])
def shop_page(request, slug):
    m = Merchant.objects.filter(slug=slug[:90], status="approved").first()
    if not m:
        return _err("Shop not found.", 404)
    return Response({"shop": _m(m, True), "products": [_p(p) for p in _public().filter(merchant=m).order_by("-sold", "-id")[:200]]})


# ---------------------------------------------------------------- merchants
def _my_merchant(u):
    return Merchant.objects.filter(user=u).first() if u.is_authenticated else None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def merchant_me(request):
    u, d = request.user, request.data
    m = _my_merchant(u)
    if request.method == "POST":
        miss = [x["label"] for x in _profile_check(u) if not x["ok"]]
        if miss and not m:
            return _err("Complete your profile first: " + ", ".join(miss) + ".", 403)
        name, city, phone = _txt(d.get("name"), 80), _txt(d.get("city"), 60), _phone(d.get("phone"))
        if len(name) < 3 or not city or not phone:
            return _err("Give your shop name, city and a phone / WhatsApp number.")
        kind = d.get("kind") if d.get("kind") in ("b2c", "b2b", "both") else "b2c"
        new = m is None
        if new:
            base = slugify(name)[:70] or "shop"
            slug, n = base, 2
            while Merchant.objects.filter(slug=slug).exists():
                slug = "%s-%d" % (base, n); n += 1
            m = Merchant(user=u, slug=slug)
        if m.status == "suspended":
            return _err("This shop is suspended. Contact us from the Ownership & complaints page.", 403)
        m.name, m.city, m.phone, m.kind = name, city, phone, kind
        m.address, m.about = _txt(d.get("address"), 200), _txt(d.get("about"), 2000)
        if m.status == "rejected":
            m.status, m.note = "pending", ""
        m.save()
        if new or m.status == "pending":
            _admins("New merchant application: %s (%s)" % (m.name, m.city))
    if not m:
        return Response({"merchant": None, "kyc": _kyc(u), "checklist": _profile_check(u)})
    paused = enforce(m) if m.status == "approved" else 0
    t = tier(m)
    stats = m.orders.aggregate(n=Count("id"))
    return Response({"merchant": dict(_m(m, True), status=m.status, note=m.note, phone=m.phone, address=m.address, about=m.about), "kyc": _kyc(u), "checklist": _profile_check(u),
                     "low_stock": m.products.filter(reorder_level__gt=0, stock__lte=F("reorder_level")).count(),
                     "tier": t, "limit": TIERS[t]["limit"], "live": m.products.filter(active=True).count(), "until": _until(m), "paused_now": paused,
                     "orders_new": m.orders.filter(status__in=("placed", "confirmed")).count(), "orders_all": stats["n"],
                     "quotes_open": Quote.objects.filter(product__merchant=m, status="open").count()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def merchant_logo(request):
    m = _my_merchant(request.user)
    if not m:
        return _err("Apply as a merchant first.", 403)
    rel = _save_pic(request.FILES.get("file"), "store/logo", m.id, (400, 400), False)
    if isinstance(rel, Response):
        return rel
    m.logo = rel; m.save(update_fields=["logo"])
    return Response(_m(m, True))


# ---------------------------------------------------------------- orders
def _o(o, viewer, full=False):
    role = "buyer" if viewer.pk == o.buyer_id else ("seller" if viewer.pk == o.merchant.user_id else "team")
    d = {"id": o.id, "no": "XS-%06d" % o.id, "group": o.group, "items": o.items, "subtotal": o.subtotal, "delivery": o.delivery, "total": o.total, "fee": o.fee,
         "payment": o.payment, "status": o.status, "role": role, "shop": {"name": o.merchant.name, "slug": o.merchant.slug},
         "created": o.created_at.isoformat(), "courier": o.courier, "tracking": o.tracking, "rating": o.rating,
         "test": o.provider in ("test", "safepay-sandbox"), "buyer": (getattr(o.buyer, "full_name", "") or o.buyer.username)[:60]}
    if full or role != "buyer":
        d.update({"name": o.name, "phone": o.phone, "address": o.address, "city": o.city, "note": o.note, "problem": o.problem, "review": o.review,
                  "times": {k: (getattr(o, k).isoformat() if getattr(o, k) else "") for k in ("paid_at", "shipped_at", "delivered_at", "done_at")}})
    if full:
        d["shop_phone"] = o.merchant.phone if role == "buyer" else ""
        d["reviewed"] = list(Review.objects.filter(order=o).values_list("product_id", flat=True))
    return d


def _stock(items, sign, order=None):
    """sign -1: sold (stock out), +1: cancelled / returned (stock back). Every change is written to the inventory ledger."""
    for it in items:
        Product.objects.filter(pk=it["id"]).update(stock=F("stock") + sign * it["qty"], sold=F("sold") - sign * it["qty"])
        if Product.objects.filter(pk=it["id"]).exists():
            StockMove.objects.create(product_id=it["id"], kind="sale" if sign < 0 else "return", qty=sign * it["qty"], unit=it["price"],
                                     party=(order.name if order else "")[:120], note=("Order XS-%06d" % order.id) if order else "", order=order)
            p = Product.objects.filter(pk=it["id"]).select_related("merchant__user").first()
            if sign < 0 and p and p.reorder_level and p.stock <= p.reorder_level:
                _notify(p.merchant.user, "Low stock: %s has %d left (reorder level %d)" % (p.title[:50], p.stock, p.reorder_level), "/store#inventory")


def _paid(o):
    if o.status != "pending":
        return
    o.status, o.paid_at = "placed", timezone.now()
    o.save(update_fields=["status", "paid_at"])
    _stock(o.items, -1, o)
    _notify(o.merchant.user, "New paid order %s: Rs %s" % ("XS-%06d" % o.id, "{:,}".format(o.total)), "/store#sorder-%d" % o.id)


def _settle(o, wait=0):
    if o.status != "pending" or not o.provider.startswith("safepay-") or not o.provider_ref:
        return o.status != "pending"
    import time
    sv = _shop()
    grp = list(Order.objects.filter(provider_ref=o.provider_ref, status="pending"))
    want = sum(x.total for x in Order.objects.filter(provider_ref=o.provider_ref))
    for i in range(wait + 1):
        st, amt = sv.sp3_info(o.provider_ref)
        if st == "TRACKER_ENDED":
            if amt is not None and int(amt) != int(want) * 100:
                Order.objects.filter(provider_ref=o.provider_ref).update(problem=("amount mismatch: safepay %s, cart %s" % (amt, want * 100))[:300])
                return False
            for x in grp:
                _paid(x)
            return True
        if i < wait:
            time.sleep(2)
    return False


def _complete(o, why=""):
    with transaction.atomic():
        o = Order.objects.select_for_update().get(pk=o.pk)
        if o.status not in ("shipped", "delivered", "disputed", "confirmed", "placed"):
            return o
        o.status, o.done_at = "completed", timezone.now()
        o.save(update_fields=["status", "done_at"])
        if o.payment == "online":
            try:
                from market.models import Entry
                Entry.objects.create(user_id=o.merchant.user_id, amount=o.total - o.fee, kind="store",
                                     note="Store order XS-%06d (Rs %s minus %d%% fee)" % (o.id, "{:,}".format(o.total), FEE_PCT))
            except Exception:
                pass
            _notify(o.merchant.user, "Order XS-%06d completed: Rs %s added to your balance" % (o.id, "{:,}".format(o.total - o.fee)), "/market#wallet")
    return o


def _auto(qs):
    now = timezone.now()
    for o in qs.filter(payment="online", status="delivered", delivered_at__lt=now - timedelta(days=AUTO_DONE_DAYS))[:30]:
        _complete(o)
    for o in qs.filter(payment="online", status="shipped", shipped_at__lt=now - timedelta(days=14))[:30]:
        _complete(o)


def _start_pay(os_, u):
    """One Safepay payment for every order in the cart (os_ = list of orders of one group)."""
    o = os_[0]
    total = sum(x.total for x in os_)
    sv = _shop()
    if not _can_pay_online(u):
        return None, "Online payment is not switched on yet. Choose cash on delivery."
    if sv.sp_ready():
        c = sv._sp3()
        try:
            dd = sv._sp3_call("POST", "/order/payments/v3/", {"merchant_api_key": c["pub"], "intent": "CYBERSOURCE", "mode": "payment", "entry_mode": "raw",
                                                             "currency": "PKR", "amount": int(total) * 100,
                                                             "metadata": {"store_group": o.group, "source": "xpertcreation"}, "include_fees": False})
            tracker = dd["data"]["tracker"]["token"]
            tbt = sv._sp3_call("POST", "/client/passport/v1/token")["data"]
        except Exception as ex:
            o.problem = ("could not start payment: %s" % ex)[:300]; o.save(update_fields=["problem"])
            return None, "Could not start the payment. Please try again in a minute."
        Order.objects.filter(pk__in=[x.pk for x in os_]).update(provider="safepay-" + c["env"], provider_ref=tracker)
        q = {"environment": c["env"], "tracker": tracker, "tbt": tbt, "source": "hosted",
             "redirect_url": SITE + "/api/store/pay/return/", "cancel_url": SITE + "/store?cancel=1#orders"}
        return {"checkout": c["checkout"] + "?" + urllib.parse.urlencode(q)}, None
    if _mode() == "test" and _staff(u):
        Order.objects.filter(pk__in=[x.pk for x in os_]).update(provider="test")
        return {"simulate": True}, None
    return None, "Online payment is not switched on yet. Choose cash on delivery."


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def orders(request):
    u, d = request.user, request.data
    if request.method == "POST":
        # The cart: products from any number of shops. One order per shop, all in one group; online = one payment for all.
        name, phone, addr, city = _txt(d.get("name"), 80), _phone(d.get("phone")), _txt(d.get("address"), 300), _txt(d.get("city"), 60)
        if len(name) < 3 or not phone or len(addr) < 8 or not city:
            return _err("Give your name, phone number, full address and city.")
        pay = "online" if d.get("payment") == "online" else "cod"
        raw = d.get("items") if isinstance(d.get("items"), list) else []
        if not raw:
            return _err("Your cart is empty.")
        grp = secrets.token_hex(6)
        made = []
        with transaction.atomic():
            byshop = {}
            for it in raw[:60]:
                p = Product.objects.select_for_update().select_related("merchant").filter(pk=_int(it.get("id"), 1, 2 ** 62) or 0, active=True, hidden=False,
                                                                                           merchant__status="approved").first()
                qty = _int(it.get("qty"), 1, 100000)
                if not p or not qty:
                    return _err("A product in your cart is no longer available. Remove it and try again.")
                if p.merchant.user_id == u.pk:
                    return _err("\"%s\" is from your own shop. Remove it from the cart." % p.title[:60])
                if qty > p.stock:
                    return _err("Only %d left of \"%s\"." % (p.stock, p.title[:60]))
                if pay == "cod" and not p.cod:
                    return _err("\"%s\" cannot be paid cash on delivery. Choose online payment, or remove it." % p.title[:60])
                if pay == "online" and not p.online:
                    return _err("\"%s\" is cash on delivery only. Choose cash on delivery, or remove it." % p.title[:60])
                ws = bool(p.wholesale_price and p.moq and qty >= p.moq)
                unit = p.wholesale_price if ws else p.price
                byshop.setdefault(p.merchant, []).append({"id": p.id, "title": p.title[:150], "price": unit, "qty": qty,
                                                          "image": ("/media/" + p.images[0]) if p.images else "", "wholesale": ws, "_fee": p.delivery_fee})
            for m, items in byshop.items():
                sub = sum(x["price"] * x["qty"] for x in items)
                deliv = max(x.pop("_fee") for x in items)
                total = sub + deliv
                o = Order.objects.create(buyer=u, merchant=m, items=items, subtotal=sub, delivery=deliv, total=total, group=grp,
                                         fee=int(round(total * FEE_PCT / 100.0)) if pay == "online" else 0, payment=pay,
                                         status="pending" if pay == "online" else "placed", name=name, phone=phone, address=addr, city=city,
                                         note=_txt(d.get("note"), 300))
                made.append(o)
                if pay == "cod":
                    _stock(items, -1, o)
        if pay == "cod":
            for o in made:
                _notify(o.merchant.user, "New cash-on-delivery order %s: Rs %s" % ("XS-%06d" % o.id, "{:,}".format(o.total)), "/store#sorder-%d" % o.id)
            return Response({"orders": [_o(o, u, True) for o in made], "group": grp}, status=201)
        res, err = _start_pay(made, u)
        if err:
            Order.objects.filter(group=grp).update(status="cancelled")
            return _err(err, 403)
        return Response(dict(res, orders=[_o(o, u, True) for o in made], group=grp), status=201)
    qs = Order.objects.filter(buyer=u).select_related("merchant")
    for o in qs.filter(status="pending", provider__startswith="safepay-", created_at__gte=timezone.now() - timedelta(hours=3))[:3]:
        _settle(o)
    _auto(qs)
    return Response({"orders": [_o(o, u) for o in qs.exclude(status="cancelled", paid_at__isnull=True, payment="online")[:100]]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def seller_orders(request):
    m = _my_merchant(request.user)
    if not m:
        return Response({"orders": []})
    qs = m.orders.select_related("merchant", "buyer").exclude(status__in=("pending",))
    _auto(qs)
    st = request.GET.get("status")
    if st:
        qs = qs.filter(status=st)
    return Response({"orders": [_o(o, request.user) for o in qs[:200]]})


def _mine(request, pk):
    o = Order.objects.select_related("merchant", "merchant__user", "buyer").filter(pk=pk).first()
    u = request.user
    if not o or not (u.pk in (o.buyer_id, o.merchant.user_id) or _staff(u)):
        return None
    return o


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order(request, pk):
    o = _mine(request, pk)
    if not o:
        return _err("Order not found.", 404)
    if o.status == "pending":
        _settle(o); o.refresh_from_db()
    return Response(_o(o, request.user, True))


@csrf_exempt
def pay_return(request):
    d = request.POST if request.method == "POST" else request.GET
    tr = (d.get("tracker") or "").strip()
    o = Order.objects.filter(provider_ref=tr).first() if tr.startswith("track_") else None
    if not o:
        return HttpResponseRedirect("/store?failed=1#orders")
    _settle(o, wait=3)
    o.refresh_from_db()
    return HttpResponseRedirect("/store?%s=1#orders" % ("paid" if o.status != "pending" else "failed"))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order_act(request, pk, act):
    u, d = request.user, request.data
    o = _mine(request, pk)
    if not o:
        return _err("Order not found.", 404)
    B, S = u.pk == o.buyer_id, u.pk == o.merchant.user_id
    link = "/store#order-%d" % o.id
    if act == "pay" and B and o.status == "pending":
        res, err = _start_pay(list(Order.objects.filter(group=o.group, status="pending")) if o.group else [o], u)
        return Response(res) if res else _err(err, 403)
    if act == "simulate":
        if not (B and o.status == "pending" and o.provider == "test" and _mode() == "test" and _staff(u)):
            return _err("Only the team, in test mode.", 403)
        for x in (Order.objects.filter(group=o.group, status="pending") if o.group else [o]):
            x.provider_ref = "TEST-%d" % x.id; x.save(update_fields=["provider_ref"]); _paid(x)
    elif act == "confirm" and S and o.status == "placed":
        o.status = "confirmed"; o.save(update_fields=["status"])
        _notify(o.buyer, "%s confirmed your order %s" % (o.merchant.name, "XS-%06d" % o.id), link)
    elif act == "ship" and S and o.status in ("placed", "confirmed"):
        courier, tr = _txt(d.get("courier"), 40), _txt(d.get("tracking"), 60)
        if not courier:
            return _err("Choose the courier (or Own delivery).")
        o.status, o.courier, o.tracking, o.shipped_at = "shipped", courier, tr, timezone.now()
        o.save(update_fields=["status", "courier", "tracking", "shipped_at"])
        _notify(o.buyer, "Your order %s is on the way (%s %s)" % ("XS-%06d" % o.id, courier, tr), link)
    elif act == "delivered" and (S or B) and o.status == "shipped":
        o.status, o.delivered_at = "delivered", timezone.now(); o.save(update_fields=["status", "delivered_at"])
        if o.payment == "cod" or B:
            o = _complete(o)
    elif act == "received" and B and o.status in ("shipped", "delivered"):
        o = _complete(o)
    elif act == "cancel":
        if B and o.status in ("pending",):
            o.status = "cancelled"; o.save(update_fields=["status"])
        elif (B or S) and o.status in ("placed", "confirmed"):
            o.status = "refund_due" if (o.payment == "online" and o.paid_at) else "cancelled"
            o.problem = ("Cancelled by the %s. %s" % ("buyer" if B else "shop", _txt(d.get("text"), 200)))[:300]
            o.save(update_fields=["status", "problem"])
            _stock(o.items, 1, o)
            _notify(o.merchant.user if B else o.buyer, "Order %s was cancelled" % ("XS-%06d" % o.id), link)
            if o.status == "refund_due":
                _admins("Refund due on store order XS-%06d" % o.id)
        else:
            return _err("This order cannot be cancelled now. Report a problem instead.", 403)
    elif act == "dispute" and (B or S) and o.status in ("confirmed", "placed", "shipped", "delivered"):
        txt = _txt(d.get("text"), 280)
        if len(txt) < 10:
            return _err("Explain the problem (10+ letters).")
        o.status, o.problem = "disputed", ("By %s: %s" % ("buyer" if B else "shop", txt))[:300]; o.save(update_fields=["status", "problem"])
        _admins("Problem on store order XS-%06d" % o.id)
    elif act == "review" and B and o.status == "completed":
        r, pid = _int(d.get("rating"), 1, 5), _int(d.get("product"), 1, 2 ** 62)
        if r is None or not any(it["id"] == pid for it in o.items):
            return _err("Pick the product and 1 to 5 stars.")
        if Review.objects.filter(order=o, product_id=pid).exists():
            return _err("You already reviewed this product.")
        if Product.objects.filter(pk=pid).exists():
            Review.objects.create(order=o, product_id=pid, buyer=u, rating=r, text=_txt(d.get("text"), 800))
            Product.objects.filter(pk=pid).update(rating_sum=F("rating_sum") + r, rating_n=F("rating_n") + 1)
        if not o.rating:
            o.rating = r; o.save(update_fields=["rating"])
            Merchant.objects.filter(pk=o.merchant_id).update(rating_sum=F("rating_sum") + r, rating_n=F("rating_n") + 1)
        _notify(o.merchant.user, "New %d-star review on %s" % (r, "XS-%06d" % o.id), "/store#p-%d" % pid)
    elif act == "reply" and S:
        rv = Review.objects.filter(pk=_int(d.get("review"), 1, 2 ** 62) or 0, product__merchant=o.merchant).first()
        if not rv:
            return _err("Review not found.", 404)
        rv.reply = _txt(d.get("text"), 500); rv.save(update_fields=["reply"])
    else:
        return _err("That does not fit this order now.", 403)
    o.refresh_from_db()
    return Response(_o(o, u, True))


# ---------------------------------------------------------------- B2B quotes
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def quotes(request):
    u, d = request.user, request.data
    if request.method == "POST":
        p = _public().filter(pk=_int(d.get("product"), 1, 2 ** 62) or 0).first()
        if not p:
            return _err("Product not found.", 404)
        if p.merchant.user_id == u.pk:
            return _err("This is your own product.")
        qty, phone = _int(d.get("qty"), 1, 10 ** 7), _phone(d.get("phone"))
        if not qty or not phone:
            return _err("Give the quantity you need and your phone number.")
        q = Quote.objects.create(product=p, buyer=u, qty=qty, phone=phone, company=_txt(d.get("company"), 120), message=_txt(d.get("message"), 1000))
        _notify(p.merchant.user, "Quote request: %d x %s" % (qty, p.title[:50]), "/store#quotes")
        return Response({"id": q.id}, status=201)
    m = _my_merchant(u)
    out = lambda q, side: {"id": q.id, "product": {"id": q.product_id, "title": q.product.title, "price": q.product.price, "image": ("/media/" + q.product.images[0]) if q.product.images else ""},
                           "qty": q.qty, "message": q.message, "company": q.company, "status": q.status, "reply": q.reply, "reply_price": q.reply_price,
                           "when": q.created_at.isoformat(), "side": side, "shop": q.product.merchant.name,
                           "buyer": (getattr(q.buyer, "full_name", "") or q.buyer.username)[:60], "phone": q.phone if side == "seller" else (q.product.merchant.phone if q.status == "answered" else "")}
    mine = [out(q, "buyer") for q in Quote.objects.filter(buyer=u).select_related("product", "product__merchant", "buyer")[:100]]
    inbox = [out(q, "seller") for q in Quote.objects.filter(product__merchant=m).select_related("product", "product__merchant", "buyer")[:200]] if m else []
    return Response({"sent": mine, "inbox": inbox})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def quote_reply(request, pk):
    q = Quote.objects.select_related("product__merchant", "buyer").filter(pk=pk, product__merchant__user=request.user).first()
    if not q:
        return _err("Quote not found.", 404)
    if request.data.get("close"):
        q.status = "closed"; q.save(update_fields=["status"]); return Response({"ok": True})
    price = _int(request.data.get("price"), 1, 10 ** 8)
    if not price:
        return _err("Give your price per unit.")
    q.reply_price, q.reply, q.status = price, _txt(request.data.get("text"), 1000), "answered"
    q.save(update_fields=["reply_price", "reply", "status"])
    _notify(q.buyer, "%s answered your quote: Rs %s per unit" % (q.product.merchant.name, "{:,}".format(price)), "/store#quotes")
    return Response({"ok": True})


# ---------------------------------------------------------------- the team
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    u = request.user
    if not _staff(u):
        return _err("Team only.", 403)
    apps = [dict(_m(m, True), status=m.status, phone=m.phone, address=m.address, user=m.user.username, kyc=_kyc(m.user), note=m.note)
            for m in Merchant.objects.filter(status__in=("pending",)).select_related("user")[:100]]
    shops = [dict(_m(m), status=m.status, user=m.user.username, live=m.products.filter(active=True).count())
             for m in Merchant.objects.exclude(status="pending").select_related("user").order_by("-id")[:200]]
    os_ = [_o(o, u, True) for o in Order.objects.filter(status__in=("disputed", "refund_due")).select_related("merchant", "merchant__user", "buyer")[:100]]
    done = Order.objects.filter(status="completed")
    return Response({"applications": apps, "shops": shops, "orders": os_,
                     "totals": {"orders": done.count(), "sales": done.aggregate(s=Sum("total"))["s"] or 0, "fees": done.aggregate(s=Sum("fee"))["s"] or 0,
                                "merchants": Merchant.objects.filter(status="approved").count(), "products": _public().count()}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_act(request, kind, pk):
    u, d = request.user, request.data
    if not _staff(u):
        return _err("Team only.", 403)
    act, note = d.get("action"), _txt(d.get("note"), 300)
    if kind == "merchant":
        m = Merchant.objects.filter(pk=pk).select_related("user").first()
        if not m or act not in ("approve", "reject", "suspend"):
            return _err("Not found.", 404)
        if act == "approve" and not _kyc(m.user):
            return _err("This member's ID is not verified yet.")
        m.status = {"approve": "approved", "reject": "rejected", "suspend": "suspended"}[act]; m.note = note; m.save(update_fields=["status", "note"])
        _notify(m.user, {"approved": "Your shop %s is approved. Add your products now!", "rejected": "Your shop application (%s) was not approved: " + note,
                         "suspended": "Your shop %s was suspended: " + note}[m.status].replace("%s", m.name, 1), "/store#seller")
    elif kind == "order":
        o = Order.objects.filter(pk=pk).select_related("merchant", "merchant__user", "buyer").first()
        if not o:
            return _err("Not found.", 404)
        if act == "release" and o.status == "disputed":
            _complete(o)
        elif act == "refund" and o.status == "disputed":
            o.status = "refund_due" if (o.payment == "online" and o.paid_at) else "cancelled"; o.problem = ("Team: " + note)[:300]
            o.save(update_fields=["status", "problem"])
        elif act == "refunded" and o.status == "refund_due":
            o.status, o.problem = "refunded", ("Refunded. " + note)[:300]; o.save(update_fields=["status", "problem"])
            _notify(o.buyer, "Refund sent for order XS-%06d" % o.id, "/store#order-%d" % o.id)
        else:
            return _err("That action does not fit this order now.")
    elif kind == "product":
        p = Product.objects.filter(pk=pk).first()
        if not p or act not in ("hide", "unhide"):
            return _err("Not found.", 404)
        p.hidden = act == "hide"; p.save(update_fields=["hidden"])
    else:
        return _err("Unknown.")
    return Response({"ok": True})



# ---------------------------------------------------------------- profile check (apply only with a complete profile + verified ID)
def _profile_check(u):
    return [{"key": "name", "label": "your full name", "ok": bool((getattr(u, "full_name", "") or "").strip()), "link": "/account"},
            {"key": "email", "label": "a verified email", "ok": bool(getattr(u, "is_email_verified", True)), "link": "/account"},
            {"key": "phone", "label": "a phone or WhatsApp number", "ok": bool(getattr(u, "whatsapp", "") or getattr(u, "phone", "")), "link": "/account"},
            {"key": "photo", "label": "a profile picture", "ok": bool(getattr(u, "avatar", "")), "link": "/account"},
            {"key": "kyc", "label": "an approved ID check (KYC)", "ok": _kyc(u), "link": "/get-verified"}]


# ---------------------------------------------------------------- inventory: stock, reorder level, purchases and sales, profit
def _inv(p):
    agg_in = p.moves.filter(kind__in=("purchase", "opening")).aggregate(q=Sum("qty"))
    return {"sku": p.sku, "cost_price": p.cost_price, "reorder_level": p.reorder_level, "low": bool(p.reorder_level and p.stock <= p.reorder_level),
            "bought": agg_in["q"] or 0}


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def inventory(request):
    m = _my_merchant(request.user)
    if not m or m.status != "approved":
        return _err("Only approved merchants have an inventory.", 403)
    d = request.data
    if request.method == "POST":
        p = m.products.filter(pk=_int(d.get("product"), 1, 2 ** 62) or 0).first()
        if not p:
            return _err("Product not found.", 404)
        kind = d.get("kind") if d.get("kind") in ("purchase", "adjust", "sale") else "purchase"
        qty = _int(d.get("qty"), -10 ** 6, 10 ** 6)
        if not qty or (kind in ("purchase",) and qty < 0):
            return _err("Give the quantity (a purchase adds stock; use a minus number on an adjustment to remove).")
        unit = _int(d.get("unit") or 0, 0, 10 ** 8) or 0
        if kind == "sale":                                  # a sale made outside the site (shop counter, phone)
            qty = -abs(qty)
            if -qty > p.stock:
                return _err("Only %d in stock." % p.stock)
            unit = unit or p.price
        if kind == "adjust" and p.stock + qty < 0:
            return _err("Stock cannot go below zero.")
        with transaction.atomic():
            StockMove.objects.create(product=p, kind=kind, qty=qty, unit=unit, party=_txt(d.get("party"), 120), note=_txt(d.get("note"), 200))
            Product.objects.filter(pk=p.pk).update(stock=F("stock") + qty, **({"sold": F("sold") - qty} if kind == "sale" else {}))
            if kind == "purchase" and unit:
                # keep cost price as the weighted average of what is in stock
                old_q = max(p.stock, 0)
                avg = int(round((old_q * p.cost_price + qty * unit) / float(old_q + qty))) if (old_q + qty) else unit
                Product.objects.filter(pk=p.pk).update(cost_price=avg)
    since = timezone.now() - timedelta(days=_int(request.GET.get("days"), 1, 3650) or 30)
    rows = []
    for p in m.products.order_by("title"):
        mv = p.moves.filter(created_at__gte=since)
        s_q = -(mv.filter(kind="sale").aggregate(q=Sum("qty"))["q"] or 0) - (mv.filter(kind="return").aggregate(q=Sum("qty"))["q"] or 0)
        revenue = sum(-x.qty * x.unit for x in mv.filter(kind="sale")) - sum(x.qty * x.unit for x in mv.filter(kind="return"))
        bought = sum(x.qty * x.unit for x in mv.filter(kind="purchase"))
        rows.append({"id": p.id, "title": p.title, "sku": p.sku, "image": ("/media/" + p.images[0]) if p.images else "", "stock": p.stock,
                     "reorder_level": p.reorder_level, "low": bool(p.reorder_level and p.stock <= p.reorder_level), "cost": p.cost_price, "price": p.price,
                     "stock_value": p.stock * p.cost_price, "sold_qty": s_q, "revenue": revenue, "cogs": s_q * p.cost_price,
                     "profit": revenue - s_q * p.cost_price, "purchases": bought, "active": p.active})
    tot = {k: sum(r[k] for r in rows) for k in ("stock_value", "revenue", "cogs", "profit", "purchases", "sold_qty")}
    tot["low"] = sum(1 for r in rows if r["low"])
    return Response({"rows": rows, "totals": tot})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stock_moves(request, pk):
    p = Product.objects.filter(pk=pk, merchant__user=request.user).first()
    if not p:
        return _err("Product not found.", 404)
    out, bal = [], p.stock
    for x in p.moves.all()[:300]:
        out.append({"when": x.created_at.isoformat(), "kind": dict(StockMove.KINDS).get(x.kind, x.kind), "qty": x.qty, "unit": x.unit, "party": x.party, "note": x.note, "balance": bal})
        bal -= x.qty
    return Response({"product": {"id": p.id, "title": p.title, "stock": p.stock, "cost": p.cost_price, "price": p.price, "reorder_level": p.reorder_level}, "moves": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review_reply(request, pk):
    rv = Review.objects.filter(pk=pk, product__merchant__user=request.user).first()
    if not rv:
        return _err("Review not found.", 404)
    rv.reply = _txt(request.data.get("text"), 500); rv.save(update_fields=["reply"])
    return Response({"ok": True})


# ---------------------------------------------------------------- home page showcase: only boosted things, from every part of the site
@api_view(["GET"])
@permission_classes([AllowAny])
def showcase(request):
    import random
    from django.apps import apps as A
    out = []
    try:
        from shop.models import Order as SO
    except Exception:
        return Response({"items": []})
    now = timezone.now()
    run = SO.objects.filter(status="paid", starts_at__lte=now, ends_at__gt=now,
                            product__in=("profile_boost", "featured_job", "gig_boost", "property_boost", "product_boost")).values_list("product", "target_id")
    want = {}
    for prod, tid in run:
        if tid:
            want.setdefault(prod, set()).add(tid)

    def model(lbl):
        try:
            return A.get_model(*lbl.split("."))
        except LookupError:
            return None
    U = A.get_model(*settings.AUTH_USER_MODEL.split("."))
    PP = model("network.ProProfile")
    for u in U.objects.filter(pk__in=want.get("profile_boost", ()), is_active=True)[:12]:
        pp = PP.objects.filter(user=u).first() if PP else None
        out.append({"type": "profile", "label": "Profile", "title": (getattr(u, "full_name", "") or u.username)[:60], "sub": (pp.headline if pp else "")[:80],
                    "image": _avatar(u), "link": ("/in/" + pp.slug) if pp and pp.slug else "/feed?user=%d" % u.pk})
    J = model("jobs.Job")
    if J:
        for j in J.objects.filter(pk__in=want.get("featured_job", ()), closed=False, hidden=False)[:12]:
            out.append({"type": "job", "label": "Job", "title": j.title[:70], "sub": ("%s%s" % (j.company, (" · " + j.city) if j.city else ""))[:80], "image": "", "link": "/jobs"})
    G = model("market.Gig")
    if G:
        for g in G.objects.filter(pk__in=want.get("gig_boost", ()), active=True, hidden=False)[:12]:
            out.append({"type": "gig", "label": "Service", "title": g.title[:70], "sub": "From Rs {:,}".format(g.price), "image": ("/media/" + g.images[0]) if g.images else "",
                        "link": "/market#gig-%d" % g.id, "cat": g.category})
    L = model("realestate.Listing")
    if L:
        for l in L.objects.filter(pk__in=want.get("property_boost", ()), status="active", hidden=False)[:12]:
            out.append({"type": "property", "label": "For rent" if l.purpose == "rent" else "For sale", "title": l.title[:70], "sub": "%s, %s" % (l.locality[:40], l.city),
                        "price": l.price, "rent": l.purpose == "rent", "image": ("/media/" + l.images[0]) if l.images else "", "link": "/market#prop-%d" % l.id})
    for p in _public().filter(pk__in=want.get("product_boost", ()))[:12]:
        out.append({"type": "product", "label": "Product", "title": p.title[:70], "sub": p.merchant.name[:40], "price": p.price, "old": p.old_price,
                    "image": ("/media/" + p.images[0]) if p.images else "", "link": "/store#p-%d" % p.id})
    random.shuffle(out)
    return Response({"items": out[:30]})
