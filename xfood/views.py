"""Food delivery API (/api/food/).
meta/                  kinds, cities, me
list/?city&area&q&kind restaurants (featured first, then open, then those that deliver to the area)
r/<slug>/              restaurant with menu and reviews
orders/                buyer: GET my orders, POST place an order (cash on delivery / pay at pickup)
orders/<id>/           buyer / restaurant: one order (polled for live status)
orders/<id>/<act>/     restaurant: accept, reject, out, ready, delivered, reply | buyer: cancel, rate
mine/                  restaurant owner: GET / POST my restaurant (apply / update); mine/image/ logo or cover
mine/menu/             sections;  mine/item/ add or edit an item;  mine/item/<id>/ on/off or delete
mine/orders/           restaurant's orders (polled; new orders ring)
team/                  moderators: approve / reject / suspend restaurants"""
import os
import re
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import KINDS, FoodOrder, Item, Restaurant, Section

COMMISSION_PCT = 0          # XpertCreation's share of each delivered order (taken from the restaurant's balance). 0 = free.
TZ = "Asia/Karachi"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
NO_ANSWER_MIN = 20          # an order nobody accepts in this time is closed and the buyer told
KD = dict(KINDS)
OPEN = ("placed", "accepted", "on_way", "ready")


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
        notify(user, "food", text, link)
    except Exception:
        pass


def _admins(text, link="/food#team"):
    try:
        from notifications.views import notify_admins
        notify_admins("food", text, link)
    except Exception:
        pass


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _kyc(u):
    try:
        k = getattr(u, "person_kyc", None)
        if k and k.status == "approved":
            return True
    except Exception:
        pass
    if _staff(u):
        return True
    try:
        from network.models import ProProfile
        return ProProfile.objects.filter(user=u, verified=True).exists()
    except Exception:
        return False


def _no(n):
    return "F-%05d" % n


def _now():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo(TZ))


def _open(r):
    """{"open": bool, "until" | "opens", "day"} - from the opening hours, in Pakistan time. No hours = always open."""
    h = r.hours or {}
    if not any(h.get(k) for k in DAYS):
        return {"open": True}
    now = _now()
    t, wd = now.strftime("%H:%M"), now.weekday()
    td, yd = h.get(DAYS[wd]), h.get(DAYS[(wd - 1) % 7])
    if yd and yd[1] < yd[0] and t < yd[1]:
        return {"open": True, "until": yd[1]}
    if td and ((td[0] < td[1] and td[0] <= t < td[1]) or (td[1] < td[0] and t >= td[0])):
        return {"open": True, "until": td[1]}
    for i in range(0, 8):
        x = h.get(DAYS[(wd + i) % 7])
        if x and (i > 0 or x[0] > t):
            return {"open": False, "opens": x[0], "day": "" if i == 0 else ("tomorrow" if i == 1 else DAYS[(wd + i) % 7])}
    return {"open": False}


def _hours(d):
    out = {}
    for k in DAYS:
        v = (d or {}).get(k)
        out[k] = [str(v[0]), str(v[1])] if isinstance(v, list) and len(v) == 2 and all(HHMM.match(str(x)) for x in v) and v[0] != v[1] else None
    return out


def _featured():
    try:
        from shop.models import Order as SO
        now = timezone.now()
        return set(SO.objects.filter(product="food_boost", status="paid", starts_at__lte=now, ends_at__gt=now).values_list("target_id", flat=True))
    except Exception:
        return set()


def _area_ok(r, area):
    if not r.delivers:
        return False
    zones = [z.strip().lower() for z in (r.areas or "").split(",") if z.strip()]
    if not zones:
        return True
    a = (area or "").strip().lower()
    return bool(a) and any(z in a or a in z for z in zones)


def _pic(p):
    return ("/media/" + p) if p else ""


def _r(r, full=False, area=""):
    d = {"id": r.id, "name": r.name, "slug": r.slug, "kind": r.kind, "kind_name": KD.get(r.kind, ""), "cuisines": r.cuisines, "city": r.city, "area": r.area,
         "logo": _pic(r.logo), "cover": _pic(r.cover), "delivers": r.delivers, "pickup": r.pickup, "min_order": r.min_order, "delivery_fee": r.delivery_fee,
         "free_over": r.free_over, "eta": [r.eta_min, r.eta_max], "paused": r.paused, "open": _open(r),
         "rating": round(r.rating_sum / r.rating_n, 1) if r.rating_n else None, "ratings": r.rating_n, "orders": r.orders_done,
         "here": _area_ok(r, area) if area else None}
    if full:
        d.update({"maplink": r.maplink, "about": r.about, "address": r.address, "areas": r.areas, "hours": r.hours or {k: None for k in DAYS}, "phone": r.phone})
    return d


def _item(i):
    return {"id": i.id, "name": i.name, "desc": i.desc, "price": i.price, "old_price": i.old_price, "image": _pic(i.image), "options": i.options or [],
            "available": i.available, "popular": i.popular, "section": i.section_id, "sold": i.sold}


def _o(o, viewer=None, full=True):
    r = o.restaurant
    d = {"id": o.id, "no": _no(o.id), "restaurant": {"name": r.name, "slug": r.slug, "logo": _pic(r.logo), "phone": r.phone, "address": r.address, "city": r.city},
         "items": o.items, "subtotal": o.subtotal, "delivery": o.delivery, "total": o.total, "fee": o.fee, "payment": o.payment, "mode": o.mode,
         "status": o.status, "created": o.created_at.isoformat(), "prep_min": o.prep_min, "rider": o.rider, "reason": o.reason,
         "rating": o.rating, "review": o.review, "reply": o.reply,
         "times": {k: (getattr(o, k).isoformat() if getattr(o, k) else "") for k in ("accepted_at", "out_at", "done_at")}}
    if full:
        d.update({"name": o.name, "phone": o.phone, "address": o.address, "area": o.area, "city": o.city, "note": o.note})
    if viewer is not None:
        d["role"] = "buyer" if viewer.pk == o.buyer_id else "restaurant"
    return d


def _expire():
    """Orders nobody accepted in time are closed, so a buyer is never left waiting."""
    if cache.get("xf:exp"):
        return
    cache.set("xf:exp", 1, 60)
    old = timezone.now() - timedelta(minutes=NO_ANSWER_MIN)
    for o in FoodOrder.objects.filter(status="placed", created_at__lt=old).select_related("restaurant")[:50]:
        if FoodOrder.objects.filter(pk=o.pk, status="placed").update(status="rejected", reason="The restaurant did not answer in time.") == 1:
            _notify(o.buyer, "Order %s from %s was not accepted in time. Please try another restaurant." % (_no(o.id), o.restaurant.name), "/food#o-%d" % o.id)
            _notify(o.restaurant.user, "Order %s closed: nobody accepted it in %d minutes." % (_no(o.id), NO_ANSWER_MIN), "/food#partner")


def _save_pic(f, oid, size):
    if not f:
        return None, "Choose a photo."
    if f.size > 8 * 1024 * 1024:
        return None, "The photo is over 8 MB."
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); im.load()
    except Exception:
        return None, "That file is not a photo we can read."
    im = ImageOps.exif_transpose(im).convert("RGB")
    im = ImageOps.fit(im, size, method=Image.LANCZOS)
    rel = os.path.join("food", timezone.localdate().strftime("%Y%m"), "%d_%s.webp" % (oid, secrets.token_hex(6)))
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=82)
    return rel, None


def _rm(rel):
    if rel:
        try:
            os.remove(os.path.join(str(settings.MEDIA_ROOT), rel))
        except OSError:
            pass


# ---------------------------------------------------------------- browse
@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    u = request.user
    me = None
    if u.is_authenticated:
        r = Restaurant.objects.filter(user=u).first()
        me = {"id": u.pk, "name": (getattr(u, "full_name", "") or u.username), "phone": getattr(u, "whatsapp", "") or getattr(u, "phone", "") or "",
              "staff": _staff(u), "restaurant": {"slug": r.slug, "status": r.status, "name": r.name} if r else None}
    cities = list(Restaurant.objects.filter(status="approved").exclude(city="").values_list("city", flat=True).distinct().order_by("city")[:200])
    return Response({"kinds": KINDS, "cities": cities, "me": me, "commission": COMMISSION_PCT})


@api_view(["GET"])
@permission_classes([AllowAny])
def browse(request):
    g = request.GET
    city, area, q, kind = _txt(g.get("city"), 60), _txt(g.get("area"), 80), _txt(g.get("q"), 60), g.get("kind")
    qs = Restaurant.objects.filter(status="approved")
    if city:
        qs = qs.filter(city__iexact=city)
    if kind in KD:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(cuisines__icontains=q) | Q(items__name__icontains=q, items__available=True)).distinct()
    fid = _featured()
    rows = [dict(_r(r, area=area), featured=r.id in fid) for r in qs[:300]]
    rows.sort(key=lambda x: (not x["featured"], not (x["open"]["open"] and not x["paused"]), x["here"] is False, -(x["rating"] or 0), -x["orders"]))
    return Response({"restaurants": rows})


@api_view(["GET"])
@permission_classes([AllowAny])
def restaurant(request, slug):
    r = Restaurant.objects.filter(slug=slug).first()
    u = request.user
    own = bool(r and u.is_authenticated and r.user_id == u.pk)
    if not r or (r.status != "approved" and not (own or _staff(u))):
        return _err("This restaurant is not available.", 404)
    d = _r(r, True, _txt(request.GET.get("area"), 80))
    items = r.items.all() if own else r.items.filter(available=True)
    d["sections"] = [{"id": s.id, "name": s.name} for s in r.sections.all()]
    d["items"] = [_item(i) for i in items]
    d["reviews"] = [{"rating": o.rating, "text": o.review, "reply": o.reply, "when": o.done_at.isoformat() if o.done_at else "",
                     "by": ((getattr(o.buyer, "full_name", "") or o.buyer.username or "Buyer").split(" ")[0])[:30]}
                    for o in r.orders.filter(rating__gt=0).select_related("buyer").order_by("-id")[:30]]
    d["mine"] = own
    return Response(d)


# ---------------------------------------------------------------- ordering
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def orders(request):
    u, d = request.user, request.data
    _expire()
    if request.method == "GET":
        return Response({"orders": [_o(o, u, False) for o in FoodOrder.objects.filter(buyer=u).select_related("restaurant")[:60]]})
    r = Restaurant.objects.filter(slug=str(d.get("restaurant") or "")[:90], status="approved").first()
    if not r:
        return _err("This restaurant is not available.", 404)
    if r.user_id == u.pk:
        return _err("This is your own restaurant.")
    if r.paused:
        return _err("%s is not taking orders right now. Try again a little later." % r.name)
    op = _open(r)
    if not op["open"]:
        return _err("%s is closed now%s." % (r.name, (" - opens " + (op.get("day") + " " if op.get("day") else "") + "at " + op["opens"]) if op.get("opens") else ""))
    mode = "pickup" if d.get("mode") == "pickup" else "delivery"
    if mode == "pickup" and not r.pickup:
        return _err("This restaurant does not offer pickup.")
    if mode == "delivery" and not r.delivers:
        return _err("This restaurant does pickup only.")
    name, phone = _txt(d.get("name"), 80), _phone(d.get("phone"))
    addr, area = _txt(d.get("address"), 300), _txt(d.get("area"), 80)
    if len(name) < 2 or not phone:
        return _err("Give your name and phone number.")
    if mode == "delivery":
        if len(addr) < 8 or not area:
            return _err("Give your full address and area.")
        if not _area_ok(r, area):
            return _err("%s does not deliver to %s. Choose pickup, or another restaurant." % (r.name, area))
    if FoodOrder.objects.filter(buyer=u, status__in=OPEN).count() >= 3:
        return _err("You already have 3 orders on the way. Wait for one to arrive first.")
    raw = d.get("items") if isinstance(d.get("items"), list) else []
    if not raw:
        return _err("Your cart is empty.")
    menu = {i.id: i for i in r.items.filter(available=True)}
    lines = []
    for it in raw[:40]:
        i = menu.get(_int(it.get("id"), 1, 2 ** 62) or 0)
        qty = _int(it.get("qty"), 1, 50)
        if not i or not qty:
            return _err("Something in your cart is not available any more. Remove it and try again.")
        chosen = it.get("opts") if isinstance(it.get("opts"), dict) else {}
        unit, picked = i.price, []
        for gi, grp in enumerate(i.options or []):
            sel = chosen.get(str(gi)) or chosen.get(gi) or []
            sel = [x for x in (sel if isinstance(sel, list) else [sel]) if isinstance(x, int) and 0 <= x < len(grp.get("choices", []))]
            if grp.get("need") and not sel:
                return _err("Choose %s for %s." % (grp.get("name", "an option").lower(), i.name))
            if not grp.get("multi") and len(sel) > 1:
                sel = sel[:1]
            for x in sel:
                c = grp["choices"][x]
                unit += int(c.get("price") or 0)
                picked.append(c.get("name", ""))
        lines.append({"id": i.id, "name": i.name, "qty": qty, "price": unit, "opts": ", ".join(p for p in picked if p)[:200]})
    sub = sum(x["price"] * x["qty"] for x in lines)
    if mode == "delivery" and r.min_order and sub < r.min_order:
        return _err("The minimum order for delivery is Rs %s." % "{:,}".format(r.min_order))
    deliv = 0 if mode == "pickup" or (r.free_over and sub >= r.free_over) else r.delivery_fee
    total = sub + deliv
    o = FoodOrder.objects.create(restaurant=r, buyer=u, items=lines, subtotal=sub, delivery=deliv, total=total,
                                 fee=int(round(total * COMMISSION_PCT / 100.0)), payment="cod", mode=mode, status="placed",
                                 name=name, phone=phone, address=addr if mode == "delivery" else "", area=area, city=r.city, note=_txt(d.get("note"), 300))
    _notify(r.user, "\U0001F514 New order %s: Rs %s (%s)" % (_no(o.id), "{:,}".format(total), "delivery" if mode == "delivery" else "pickup"), "/food#partner")
    return Response(_o(o, u), status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order(request, pk):
    u = request.user
    o = FoodOrder.objects.select_related("restaurant").filter(pk=pk).first()
    if not o or not (u.pk in (o.buyer_id, o.restaurant.user_id) or _staff(u)):
        return _err("Order not found.", 404)
    _expire()
    o.refresh_from_db()
    return Response(_o(o, u))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order_act(request, pk, act):
    u, d = request.user, request.data
    o = FoodOrder.objects.select_related("restaurant", "restaurant__user", "buyer").filter(pk=pk).first()
    if not o or not (u.pk in (o.buyer_id, o.restaurant.user_id)):
        return _err("Order not found.", 404)
    B, S, r = u.pk == o.buyer_id, u.pk == o.restaurant.user_id, o.restaurant
    link, now = "/food#o-%d" % o.id, timezone.now()

    def move(frm, to, **kw):
        n = FoodOrder.objects.filter(pk=o.pk, status__in=frm).update(status=to, **kw)
        if not n:
            raise ValueError
    try:
        if act == "accept" and S:
            m = _int(d.get("minutes"), 5, 180) or r.eta_min
            move(("placed",), "accepted", accepted_at=now, prep_min=m)
            _notify(o.buyer, "%s accepted your order %s - %s in about %d minutes." % (r.name, _no(o.id), "ready" if o.mode == "pickup" else "at your door", m), link)
        elif act == "reject" and S:
            why = _txt(d.get("reason"), 200) or "The restaurant could not take this order."
            move(("placed", "accepted"), "rejected", reason=why)
            _notify(o.buyer, "%s could not take your order %s: %s" % (r.name, _no(o.id), why), link)
        elif act == "out" and S and o.mode == "delivery":
            move(("accepted",), "on_way", out_at=now, rider=_txt(d.get("rider"), 80))
            _notify(o.buyer, "\U0001F6F5 Your order %s is on the way!%s" % (_no(o.id), (" Rider: " + _txt(d.get("rider"), 80)) if d.get("rider") else ""), link)
        elif act == "ready" and S and o.mode == "pickup":
            move(("accepted",), "ready", out_at=now)
            _notify(o.buyer, "Your order %s is ready for pickup at %s." % (_no(o.id), r.name), link)
        elif act == "delivered" and S:
            with transaction.atomic():
                move(("on_way", "ready", "accepted"), "delivered", done_at=now)
                Restaurant.objects.filter(pk=r.pk).update(orders_done=F("orders_done") + 1)
                for x in o.items:
                    Item.objects.filter(pk=x["id"], restaurant=r).update(sold=F("sold") + x["qty"])
                if o.fee:
                    try:
                        from market.models import Entry
                        Entry.objects.create(user_id=r.user_id, amount=-o.fee, kind="food_fee", note="Food order %s commission (%d%%)" % (_no(o.id), COMMISSION_PCT))
                    except Exception:
                        pass
            _notify(o.buyer, "Enjoy your meal! How was %s? Rate your order %s." % (r.name, _no(o.id)), link)
        elif act == "cancel" and B:
            move(("placed",), "cancelled", reason="Cancelled by the buyer.")
            _notify(r.user, "Order %s was cancelled by the buyer." % _no(o.id), "/food#partner")
        elif act == "rate" and B and o.status == "delivered" and not o.rating:
            st = _int(d.get("rating"), 1, 5)
            if not st:
                return _err("Tap 1 to 5 stars.")
            FoodOrder.objects.filter(pk=o.pk).update(rating=st, review=_txt(d.get("text"), 500))
            Restaurant.objects.filter(pk=r.pk).update(rating_sum=F("rating_sum") + st, rating_n=F("rating_n") + 1)
            _notify(r.user, "New %d-star review on order %s" % (st, _no(o.id)), "/food#partner-reviews")
        elif act == "reply" and S and o.rating:
            FoodOrder.objects.filter(pk=o.pk).update(reply=_txt(d.get("text"), 300))
        else:
            return _err("That does not fit this order now.", 403)
    except ValueError:
        return _err("The order changed - refresh to see its status.", 409)
    o.refresh_from_db()
    return Response(_o(o, u))


# ---------------------------------------------------------------- restaurant owner
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def mine(request):
    u, d = request.user, request.data
    r = Restaurant.objects.filter(user=u).first()
    if request.method == "POST":
        name, city, phone = _txt(d.get("name"), 80), _txt(d.get("city"), 60), _phone(d.get("phone"))
        addr = _txt(d.get("address"), 200)
        if len(name) < 3 or not city or not phone or len(addr) < 8:
            return _err("Give the restaurant name, city, full address and a phone / WhatsApp number.")
        if r and r.status == "suspended":
            return _err("This restaurant is suspended. Contact us from the Ownership & complaints page.", 403)
        nums = {}
        for k, lo, hi, df in (("min_order", 0, 100000, 0), ("delivery_fee", 0, 10000, 0), ("free_over", 0, 100000, 0), ("eta_min", 5, 180, 30), ("eta_max", 5, 240, 45)):
            v = _int(d.get(k) if d.get(k) not in (None, "") else df, lo, hi)
            if v is None:
                return _err("Check the numbers: minimum order, delivery fee and delivery time.")
            nums[k] = v
        if nums["eta_max"] < nums["eta_min"]:
            nums["eta_max"] = nums["eta_min"]
        new = r is None
        if new:
            base = slugify(name)[:70] or "restaurant"
            slug, n = base, 2
            while Restaurant.objects.filter(slug=slug).exists():
                slug = "%s-%d" % (base, n); n += 1
            r = Restaurant(user=u, slug=slug, status="approved" if _kyc(u) else "pending")
        r.name, r.city, r.phone, r.address = name, city, phone, addr
        r.kind = d.get("kind") if d.get("kind") in KD else "restaurant"
        r.cuisines, r.area, r.about = _txt(d.get("cuisines"), 160), _txt(d.get("area"), 80), _txt(d.get("about"), 1000)
        if "maplink" in d:
            r.maplink = maplink(d.get("maplink"))
        r.areas = ", ".join(z.strip() for z in _txt(d.get("areas"), 2000).replace("\n", ",").split(",") if z.strip())[:2000]
        r.delivers, r.pickup = bool(d.get("delivers", True)), bool(d.get("pickup", True))
        if not r.delivers and not r.pickup:
            return _err("Choose delivery, pickup, or both.")
        for k, v in nums.items():
            setattr(r, k, v)
        if "hours" in d:
            r.hours = _hours(d.get("hours") if isinstance(d.get("hours"), dict) else {})
        if "paused" in d:
            r.paused = bool(d.get("paused"))
        if r.status == "rejected":
            r.status, r.note = "pending", ""
        r.save()
        if new:
            if r.status == "pending":
                _admins("New restaurant to approve: %s (%s)" % (r.name, r.city))
                _notify(u, "We received %s. Our team checks new restaurants within 1 working day." % r.name, "/food#partner")
            else:
                _notify(u, "%s is live on Food delivery! Add your menu now." % r.name, "/food#partner-menu")
                _admins("New restaurant (ID verified, live): %s (%s)" % (r.name, r.city))
    if not r:
        return Response({"restaurant": None, "kyc": _kyc(u)})
    out = _r(r, True)
    out.update({"status": r.status, "note": r.note, "items": r.items.count(), "new": r.orders.filter(status="placed").count()})
    return Response({"restaurant": out, "kyc": _kyc(u)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def mine_image(request):
    r = Restaurant.objects.filter(user=request.user).first()
    if not r:
        return _err("Open your restaurant first.", 403)
    kind = "cover" if request.data.get("kind") == "cover" else "logo"
    rel, e = _save_pic(request.FILES.get("file"), r.id, (1200, 500) if kind == "cover" else (400, 400))
    if e:
        return _err(e)
    _rm(getattr(r, kind))
    setattr(r, kind, rel); r.save(update_fields=[kind])
    return Response({"ok": True, kind: _pic(rel)})


def _owner(u):
    return Restaurant.objects.filter(user=u).exclude(status="suspended").first()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def menu(request):
    r = _owner(request.user)
    if not r:
        return _err("Open your restaurant first.", 403)
    if request.method == "POST":
        rows = request.data.get("sections") if isinstance(request.data.get("sections"), list) else []
        keep = []
        for i, s in enumerate(rows[:40]):
            nm = _txt((s or {}).get("name"), 60)
            if not nm:
                continue
            sid = _int((s or {}).get("id"), 1, 2 ** 62)
            x = r.sections.filter(pk=sid).first() if sid else None
            if x:
                x.name, x.pos = nm, i; x.save()
            else:
                x = Section.objects.create(restaurant=r, name=nm, pos=i)
            keep.append(x.id)
        r.sections.exclude(pk__in=keep).delete()
    return Response({"sections": [{"id": s.id, "name": s.name} for s in r.sections.all()], "items": [_item(i) for i in r.items.all()]})


def _clean_opts(v):
    import json
    if isinstance(v, str):
        try:
            v = json.loads(v or "[]")
        except Exception:
            return None
    out = []
    for g in (v if isinstance(v, list) else [])[:8]:
        if not isinstance(g, dict):
            continue
        nm = _txt(g.get("name"), 40)
        ch = []
        for c in (g.get("choices") if isinstance(g.get("choices"), list) else [])[:15]:
            cn, cp = _txt((c or {}).get("name"), 40), _int((c or {}).get("price") or 0, 0, 100000)
            if cn and cp is not None:
                ch.append({"name": cn, "price": cp})
        if nm and ch:
            out.append({"name": nm, "need": bool(g.get("need")), "multi": bool(g.get("multi")), "choices": ch})
    return out


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def item_save(request):
    r = _owner(request.user)
    if not r:
        return _err("Open your restaurant first.", 403)
    d = request.data
    iid = _int(d.get("id"), 1, 2 ** 62)
    i = r.items.filter(pk=iid).first() if iid else Item(restaurant=r)
    if iid and not i:
        return _err("Item not found.", 404)
    if not i.pk and r.items.count() >= 300:
        return _err("A menu can have 300 items.")
    name, price, old = _txt(d.get("name"), 100), _int(d.get("price"), 1, 1000000), _int(d.get("old_price") or 0, 0, 1000000)
    if len(name) < 2 or not price:
        return _err("Give the item a name and a price.")
    if old is None or (old and old <= price):
        old = 0
    opts = _clean_opts(d.get("options"))
    if opts is None:
        return _err("Check the options.")
    sec = _int(d.get("section"), 1, 2 ** 62)
    i.section = r.sections.filter(pk=sec).first() if sec else None
    tb = lambda k, df: (str(d.get(k)).lower() in ("1", "true", "on", "yes")) if d.get(k) not in (None, "") else df
    i.name, i.desc, i.price, i.old_price, i.options = name, _txt(d.get("desc"), 300), price, old, opts
    i.available, i.popular = tb("available", True), tb("popular", False)
    i.save()
    f = request.FILES.get("file")
    if f:
        rel, e = _save_pic(f, i.id, (800, 600))
        if e:
            return _err(e)
        _rm(i.image)
        i.image = rel; i.save(update_fields=["image"])
    return Response(_item(i))


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def item_one(request, pk):
    r = _owner(request.user)
    i = r.items.filter(pk=pk).first() if r else None
    if not i:
        return _err("Item not found.", 404)
    if request.method == "DELETE":
        _rm(i.image); i.delete()
        return Response({"ok": True})
    i.available = bool(request.data.get("available")); i.save(update_fields=["available"])
    return Response(_item(i))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine_orders(request):
    r = Restaurant.objects.filter(user=request.user).first()
    if not r:
        return _err("Open your restaurant first.", 403)
    _expire()
    since = timezone.now() - timedelta(hours=36)
    qs = r.orders.filter(Q(status__in=OPEN) | Q(created_at__gte=since)).select_related("restaurant")[:150]
    today = r.orders.filter(status="delivered", done_at__date=timezone.localdate())
    return Response({"orders": [_o(o) for o in qs], "new": r.orders.filter(status="placed").count(),
                     "today": {"orders": today.count(), "sales": sum(today.values_list("total", flat=True))}, "paused": r.paused,
                     "reviews": [{"id": o.id, "no": _no(o.id), "rating": o.rating, "text": o.review, "reply": o.reply} for o in r.orders.filter(rating__gt=0)[:40]]})


# ---------------------------------------------------------------- team
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    if not _staff(request.user):
        return _err("Team only.", 403)
    return Response({"restaurants": [dict(_r(r, True), status=r.status, note=r.note, owner=r.user.username, created=r.created_at.isoformat())
                                     for r in Restaurant.objects.select_related("user").order_by("status", "-id")[:300]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_act(request, pk, act):
    if not _staff(request.user):
        return _err("Team only.", 403)
    r = Restaurant.objects.filter(pk=pk).select_related("user").first()
    if not r:
        return _err("Not found.", 404)
    why = _txt(request.data.get("note"), 300)
    if act == "approve":
        r.status, r.note = "approved", ""
        _notify(r.user, "%s is approved and live on Food delivery! Add your menu." % r.name, "/food#partner-menu")
    elif act == "reject":
        r.status, r.note = "rejected", why or "Please check your details."
        _notify(r.user, "%s was not approved: %s" % (r.name, r.note), "/food#partner")
    elif act == "suspend":
        r.status, r.note = "suspended", why or "Suspended by the team."
        _notify(r.user, "%s is suspended: %s" % (r.name, r.note), "/food#partner")
    else:
        return _err("Unknown action.")
    r.save(update_fields=["status", "note"])
    return Response({"ok": True, "status": r.status})


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
