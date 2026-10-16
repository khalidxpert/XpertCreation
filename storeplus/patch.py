"""Hooks into the store app (installed once, when Django starts - see apps.py). Nothing in store/ is edited.
Countries: every shop sells in one country (default Pakistan). Buyers pick a country (cookie xc_cc); lists show
only that country's shops, prices use its currency, one checkout = one country, online payment = Pakistan only.
Dropshipping: see models.py. The supplier gets a "mirror" order to ship to the customer; status and tracking copy
back to the customer's order; money is settled in the wallets when the customer's order completes."""
import contextvars
import functools
import json

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

CC = contextvars.ContextVar("xc_cc", default=None)

# code, name, currency, symbol, time zone
COUNTRIES = [
    ("PK", "Pakistan", "PKR", "Rs", "Asia/Karachi"), ("AE", "United Arab Emirates", "AED", "AED", "Asia/Dubai"),
    ("SA", "Saudi Arabia", "SAR", "SAR", "Asia/Riyadh"), ("QA", "Qatar", "QAR", "QAR", "Asia/Qatar"),
    ("KW", "Kuwait", "KWD", "KWD", "Asia/Kuwait"), ("OM", "Oman", "OMR", "OMR", "Asia/Muscat"),
    ("BH", "Bahrain", "BHD", "BHD", "Asia/Bahrain"), ("GB", "United Kingdom", "GBP", "£", "Europe/London"),
    ("US", "United States", "USD", "$", "America/New_York"), ("CA", "Canada", "CAD", "C$", "America/Toronto"),
    ("AU", "Australia", "AUD", "A$", "Australia/Sydney"), ("NZ", "New Zealand", "NZD", "NZ$", "Pacific/Auckland"),
    ("DE", "Germany", "EUR", "€", "Europe/Berlin"), ("FR", "France", "EUR", "€", "Europe/Paris"),
    ("IT", "Italy", "EUR", "€", "Europe/Rome"), ("ES", "Spain", "EUR", "€", "Europe/Madrid"),
    ("NL", "Netherlands", "EUR", "€", "Europe/Amsterdam"), ("IE", "Ireland", "EUR", "€", "Europe/Dublin"),
    ("TR", "Turkey", "TRY", "₺", "Europe/Istanbul"), ("MY", "Malaysia", "MYR", "RM", "Asia/Kuala_Lumpur"),
    ("SG", "Singapore", "SGD", "S$", "Asia/Singapore"), ("BD", "Bangladesh", "BDT", "Tk", "Asia/Dhaka"),
    ("IN", "India", "INR", "₹", "Asia/Kolkata"), ("ZA", "South Africa", "ZAR", "R", "Africa/Johannesburg"),
]
CMAP = {c[0]: c for c in COUNTRIES}


def flag(code):
    return "".join(chr(0x1F1E6 + ord(ch) - 65) for ch in code)


def cinfo(code):
    c = CMAP.get(code) or CMAP["PK"]
    return {"code": c[0], "name": c[1], "currency": c[2], "sym": c[3], "tz": c[4], "flag": flag(c[0])}


def valid_cc(v):
    v = str(v or "").upper()[:2]
    return v if v in CMAP else ""


def buyer_cc(request):
    return valid_cc(getattr(request, "GET", {}).get("cc")) or valid_cc(request.COOKIES.get("xc_cc")) or "PK"


def cc_q(code, prefix="merchant__"):
    if code == "PK":
        return Q(**{prefix + "region__isnull": True}) | Q(**{prefix + "region__country": "PK"})
    return Q(**{prefix + "region__country": code})


def shop_cc(m):
    try:
        return m.region.country or "PK"
    except Exception:
        return "PK"


def _notify(user, text, link):
    try:
        from notifications.views import notify
        notify(user, "store", text, link)
    except Exception:
        pass


def _body(request):
    try:
        d = json.loads(request.body or b"{}")
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _no(msg, code=400):
    return JsonResponse({"detail": msg}, status=code)


def _rs(n, code="PK"):
    return "%s %s" % (cinfo(code)["sym"], "{:,}".format(int(n or 0)))


# ---------------------------------------------------------------- dropshipping
def drop_sync(links=None):
    """Keep each reseller copy in step with the supplier's product: stock, photos, delivery, payment options."""
    from .models import DropLink, DropOffer
    qs = links if links is not None else DropLink.objects.all()
    for lk in qs.select_related("product", "source", "source__merchant", "product__merchant__user")[:3000]:
        p, s = lk.product, lk.source
        off = DropOffer.objects.filter(product=s).first() if s else None
        ok = bool(s and off and off.on and s.active and not s.hidden and s.merchant.status == "approved")
        want = {"stock": s.stock if ok else 0, "images": list(s.images or []) if s else list(p.images or []),
                "delivery_fee": s.delivery_fee if s else p.delivery_fee, "delivery_days": s.delivery_days if s else p.delivery_days,
                "cod": s.cod if s else p.cod, "online": s.online if s else p.online, "wholesale_price": 0, "moq": 0}
        if ok and p.active and p.price < off.price:
            want["active"] = False
            if not lk.warned:
                _notify(p.merchant.user, "Dropship: %s is paused - the supplier price is now %s, above your price. Raise your price to sell it." % (p.title[:50], _rs(off.price)), "/store#seller-drop")
                type(lk).objects.filter(pk=lk.pk).update(warned=True)
        ch = [k for k, v in want.items() if getattr(p, k) != v]
        if ch:
            for k in ch:
                setattr(p, k, want[k])
            p.save(update_fields=ch)


def drop_make(o):
    """Customer order o (with the reseller) -> the supplier's order to ship. Idempotent."""
    from store import views as sv
    from store.models import Order, Product
    from .models import DropLink, DropOffer, DropOrder
    if o.status not in ("placed", "confirmed") or DropOrder.objects.filter(order=o).exists():
        return
    links = {lk.product_id: lk for lk in DropLink.objects.filter(product_id__in=[it["id"] for it in o.items]).select_related("source", "supplier")}
    if not links:
        return
    first = next(iter(links.values()))
    sup = first.supplier
    items = []
    for it in o.items:
        lk = links.get(it["id"])
        if not lk or not lk.source:
            continue
        off = DropOffer.objects.filter(product=lk.source).first()
        unit = off.price if off else lk.source.price
        items.append({"id": lk.source_id, "title": lk.source.title[:150], "price": unit, "qty": it["qty"], "image": it.get("image", ""), "wholesale": False})
    if not items:
        return
    sub = sum(x["price"] * x["qty"] for x in items)
    deliv = max([lk.source.delivery_fee for lk in links.values() if lk.source] or [0])
    cod = o.payment == "cod"
    note = ("DROPSHIP for %s (their order XS-%06d). Ship straight to this customer, without your prices in the parcel. %s"
            % (o.merchant.name, o.id, ("Collect %s cash from the customer. You keep %s; the rest is the reseller's profit, moved from your balance to theirs." % (_rs(o.total), _rs(sub + deliv)))
               if cod else "Already paid online - do not collect money. You get %s in your balance when the customer receives it." % _rs(sub + deliv)))[:300]
    with transaction.atomic():
        mo = Order.objects.create(buyer=o.merchant.user, merchant=sup, items=items, subtotal=sub, delivery=deliv, total=sub + deliv, fee=0,
                                  payment="drop", status="placed", name=o.name, phone=o.phone, address=o.address, city=o.city, note=note, group="")
        DropOrder.objects.create(order=o, mirror=mo, cost=sub + deliv)
    sv._stock(items, -1, mo)
    _notify(sup.user, "New dropship order XS-%06d from %s: ship to %s, %s" % (mo.id, o.merchant.name, o.name, o.city), "/store#sorder-%d" % mo.id)
    drop_sync(DropLink.objects.filter(source_id__in=[x["id"] for x in items]))


def drop_settle(o):
    """Customer order o completed -> complete the supplier's order and move the money."""
    from .models import DropOrder
    d = DropOrder.objects.filter(order=o, settled=False).select_related("mirror", "mirror__merchant", "order__merchant").first()
    if not d:
        return
    from store.models import Order
    from market.models import Entry
    with transaction.atomic():
        if DropOrder.objects.filter(pk=d.pk, settled=False).update(settled=True) != 1:
            return
        Order.objects.filter(pk=d.mirror_id).update(status="completed", done_at=timezone.now())
        res, sup = o.merchant.user_id, d.mirror.merchant.user_id
        if o.payment == "online":
            Entry.objects.create(user_id=res, amount=-d.cost, kind="dropship", note=("Dropship cost XS-%06d paid to %s" % (o.id, d.mirror.merchant.name))[:200])
            Entry.objects.create(user_id=sup, amount=d.cost, kind="dropship", note=("Dropship XS-%06d for %s" % (d.mirror_id, o.merchant.name))[:200])
            _notify(d.mirror.merchant.user, "Dropship order XS-%06d completed: %s added to your balance" % (d.mirror_id, _rs(d.cost)), "/market#wallet")
        else:
            margin = o.total - d.cost
            if margin:
                Entry.objects.create(user_id=sup, amount=-margin, kind="dropship", note=("Reseller profit on XS-%06d (you collected %s cash)" % (d.mirror_id, _rs(o.total)))[:200])
                Entry.objects.create(user_id=res, amount=margin, kind="dropship", note=("Dropship profit on XS-%06d" % o.id)[:200])
            _notify(o.merchant.user, "Dropship order XS-%06d completed: profit %s added to your balance" % (o.id, _rs(margin)), "/market#wallet")


def _sync_from_mirror(d, act):
    from store import views as sv
    from store.models import Order
    s = Order.objects.select_related("merchant", "buyer").get(pk=d.order_id)
    mo = Order.objects.get(pk=d.mirror_id)
    link = "/store#order-%d" % s.id
    if act == "confirm" and s.status == "placed":
        Order.objects.filter(pk=s.pk).update(status="confirmed")
    elif act == "ship" and s.status in ("placed", "confirmed"):
        Order.objects.filter(pk=s.pk).update(status="shipped", courier=mo.courier, tracking=mo.tracking, shipped_at=timezone.now())
        _notify(s.buyer, "Your order XS-%06d is on the way (%s %s)" % (s.id, mo.courier, mo.tracking), link)
        _notify(s.merchant.user, "Supplier shipped your dropship order XS-%06d (%s %s)" % (s.id, mo.courier, mo.tracking), "/store#sorder-%d" % s.id)
    elif act == "delivered" and s.status == "shipped":
        Order.objects.filter(pk=s.pk).update(status="delivered", delivered_at=timezone.now())
        s.refresh_from_db()
        if s.payment == "cod":
            sv._complete(s)
        else:
            _notify(s.buyer, "Order XS-%06d is delivered. Tap Received in My orders." % s.id, link)
    elif act == "cancel" and mo.status in ("cancelled", "refund_due"):
        _notify(s.merchant.user, "The supplier cancelled dropship order XS-%06d. Cancel your order XS-%06d or contact the customer." % (mo.id, s.id), "/store#sorder-%d" % s.id)


# ---------------------------------------------------------------- install
def install():
    from store import views as sv
    from .models import DropLink, DropOrder, Region

    def wrap(name):
        def deco(fn):
            orig = getattr(sv, name)

            @functools.wraps(orig)
            def w(request, *a, **k):
                return fn(orig, request, *a, **k)
            setattr(sv, name, w)
            return fn
        return deco

    # lists show the buyer's country only
    _pub = sv._public

    def _public():
        qs = _pub()
        c = CC.get()
        return qs.filter(cc_q(c)) if c else qs
    sv._public = _public

    def _with(code, f):
        t = CC.set(code)
        try:
            return f()
        finally:
            CC.reset(t)

    @wrap("home")
    def home(orig, request, *a, **k):
        return _with(buyer_cc(request), lambda: orig(request, *a, **k))

    @wrap("meta")
    def meta(orig, request, *a, **k):
        r = orig(request, *a, **k)
        code = buyer_cc(request)
        try:
            ci = cinfo(code)
            r.data.update({"cc": code, "country": ci, "cur": ci["sym"], "countries": [cinfo(c[0]) for c in COUNTRIES]})
            me = r.data.get("me") or {}
            mm = me.get("merchant")
            if mm:
                from store.models import Merchant
                m = Merchant.objects.filter(pk=mm["id"]).first()
                mc = shop_cc(m) if m else "PK"
                r.data["mycc"], r.data["mycur"] = mc, cinfo(mc)["sym"]
            if not cache.get("sp:sync"):
                cache.set("sp:sync", 1, 600)
                drop_sync()
        except Exception:
            pass
        return r

    def _after_save(r, request):
        try:
            if getattr(r, "status_code", 500) >= 300 or not isinstance(r.data, dict) or not r.data.get("id"):
                return r
            from store.models import Product
            p = Product.objects.select_related("merchant").get(pk=r.data["id"])
            if shop_cc(p.merchant) != "PK" and (p.online or not p.cod):
                Product.objects.filter(pk=p.pk).update(online=False, cod=True)
                r.data.update({"online": False, "cod": True})
            if DropLink.objects.filter(product=p).exists():
                drop_sync(DropLink.objects.filter(product=p))
                p.refresh_from_db()
                r.data.update({"stock": p.stock, "active": p.active and not p.hidden, "images": ["/media/" + x for x in (p.images or [])]})
        except Exception:
            pass
        return r

    @wrap("products")
    def products(orig, request, *a, **k):
        if request.method == "POST":
            return _after_save(orig(request, *a, **k), request)
        return _with(buyer_cc(request), lambda: orig(request, *a, **k))

    @wrap("product")
    def product(orig, request, pk, *a, **k):
        from store.models import Product
        p = Product.objects.select_related("merchant").filter(pk=pk).first()
        lk = DropLink.objects.filter(product_id=pk).first() if p else None
        if request.method == "DELETE" and lk:
            Product.objects.filter(pk=pk).update(images=[])          # the photos belong to the supplier
        if request.method == "GET" and lk:
            drop_sync(DropLink.objects.filter(pk=lk.pk))
        if request.method == "POST":
            return _after_save(orig(request, pk, *a, **k), request)
        code = shop_cc(p.merchant) if p else "PK"
        r = _with(code, lambda: orig(request, pk, *a, **k))
        try:
            if request.method == "GET" and isinstance(r.data, dict) and r.data.get("id"):
                r.data.update({"country": code, "cur": cinfo(code)["sym"], "dropship": bool(lk)})
        except Exception:
            pass
        return r

    @wrap("product_image")
    def product_image(orig, request, pk, *a, **k):
        if DropLink.objects.filter(product_id=pk).exists():
            return _no("This is a dropship product: its photos come from the supplier.", 403)
        return orig(request, pk, *a, **k)

    @wrap("merchant_me")
    def merchant_me(orig, request, *a, **k):
        want = valid_cc(_body(request).get("country")) if request.method == "POST" else ""
        r = orig(request, *a, **k)
        try:
            if want and getattr(r, "status_code", 500) < 300:
                from store.models import Merchant
                m = Merchant.objects.filter(user=request.user).first() if request.user.is_authenticated else None
                if m and not m.orders.exists():
                    Region.objects.update_or_create(merchant=m, defaults={"country": want})
        except Exception:
            pass
        return r

    @wrap("orders")
    def orders(orig, request, *a, **k):
        if request.method != "POST":
            r = orig(request, *a, **k)
            try:
                rows = r.data.get("orders") if isinstance(r.data, dict) else None
                if rows:
                    hide = set(DropOrder.objects.filter(mirror_id__in=[x["id"] for x in rows]).values_list("mirror_id", flat=True))
                    if hide:
                        r.data["orders"] = [x for x in rows if x["id"] not in hide]
            except Exception:
                pass
            return r
        from store.models import Product
        d = _body(request)
        ids = []
        for it in (d.get("items") if isinstance(d.get("items"), list) else [])[:60]:
            try:
                ids.append(int(it.get("id")))
            except Exception:
                pass
        ps = list(Product.objects.filter(pk__in=ids).select_related("merchant"))
        drop_sync(DropLink.objects.filter(product__in=ps))
        ccs = set(shop_cc(p.merchant) for p in ps)
        if len(ccs) > 1:
            return _no("Your cart has shops from different countries. Order from one country at a time.")
        if ccs and ccs != {"PK"} and d.get("payment") == "online":
            return _no("Online payment is for shops in Pakistan only. Choose cash on delivery.")
        links = {lk.product_id: lk for lk in DropLink.objects.filter(product__in=ps)}
        by = {}
        for p in ps:
            by.setdefault(p.merchant_id, []).append(p)
        for mid, group in by.items():
            dl = [links.get(p.id) for p in group]
            if any(dl):
                sups = set(x.supplier_id if x else None for x in dl)
                if len(sups) > 1:
                    bad = next(p for p in group if links.get(p.id))
                    return _no("\"%s\" is sent by another seller. Order it on its own, without other items from %s." % (bad.title[:60], bad.merchant.name))
        r = orig(request, *a, **k)
        try:
            if getattr(r, "status_code", 500) == 201 and d.get("payment") != "online":
                from store.models import Order
                for x in r.data.get("orders", []):
                    drop_make(Order.objects.select_related("merchant").get(pk=x["id"]))
        except Exception:
            pass
        return r

    _paid = sv._paid

    def paid(o):
        _paid(o)
        try:
            o.refresh_from_db()
            drop_make(o)
        except Exception:
            pass
    sv._paid = paid

    _complete = sv._complete

    def complete(o, why=""):
        r = _complete(o, why)
        try:
            if r.status == "completed":
                drop_settle(r)
        except Exception:
            pass
        return r
    sv._complete = complete

    @wrap("order_act")
    def order_act(orig, request, pk, act, *a, **k):
        u = request.user
        mir = DropOrder.objects.filter(mirror_id=pk).select_related("order", "mirror").first()
        src = None if mir else DropOrder.objects.filter(order_id=pk).select_related("order", "order__merchant", "mirror").first()
        if mir and u.is_authenticated and u.pk == mir.mirror.buyer_id and act in ("received", "cancel", "delivered", "review", "pay"):
            return _no("This is the supplier's copy of your dropship order. Manage it from your order XS-%06d." % mir.order_id, 403)
        if src and u.is_authenticated and u.pk == src.order.merchant.user_id and act in ("ship", "delivered"):
            return _no("The supplier ships this dropship order. The tracking shows here when they ship it.", 403)
        r = orig(request, pk, act, *a, **k)
        try:
            if getattr(r, "status_code", 500) < 300:
                if mir:
                    _sync_from_mirror(mir, act)
                elif src and act == "cancel":
                    from store.models import Order
                    mo = Order.objects.get(pk=src.mirror_id)
                    if mo.status in ("placed", "confirmed"):
                        Order.objects.filter(pk=mo.pk).update(status="cancelled", problem="The customer's order was cancelled.")
                        sv._stock(mo.items, 1, mo)
                        _notify(mo.merchant.user, "Dropship order XS-%06d was cancelled - do not ship it." % mo.id, "/store#sorder-%d" % mo.id)
        except Exception:
            pass
        return r

    # yellow pages (store chat app): the buyer's country only
    try:
        from storechat import views as cv
        _dir = cv.directory

        @functools.wraps(_dir)
        def directory(request, *a, **k):
            return _with(buyer_cc(request), lambda: _dir(request, *a, **k))
        cv.directory = directory
        _mq = cv.Merchant

        class _M:
            class objects:
                @staticmethod
                def filter(*a, **k):
                    qs = _mq.objects.filter(*a, **k)
                    c = CC.get()
                    return qs.filter(cc_q(c, "")) if c else qs
        cv.Merchant = _M
    except Exception:
        pass
