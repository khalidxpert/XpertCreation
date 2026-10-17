"""XpertWheels API (/api/wheels/).
meta/                  makes, models, options, cities, me
ads/                   GET browse (filters, sort, page) | POST new ad
ads/<id>/              GET one ad (with price guide and more from the seller) | POST edit | DELETE
ads/<id>/image/        POST add a photo (file) / remove (remove=i) / make first (first=i)
ads/<id>/phone/        signed in: the seller's number (counted)
ads/<id>/offer/        signed in: make an offer -> the seller gets a bell
ads/<id>/report/       signed in: report the ad -> moderators get a bell
ads/<id>/<act>/        owner: sold, pause, live
mine/                  my ads and the offers on them
offers/<id>/reply/     owner: answer an offer
team/                  moderators: reported and recent ads; team/<id>/hide|show|done
og/<id>/               link preview for xpertcreation.com/wheels?ad=<id> (nginx sends it here)"""
import html as _h
import os
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.db.models import F, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .data import BODY, CITIES, FEATURES, FUEL, MAKES, TRANS
from .models import KINDS, Ad, Offer, Report

FREE_ADS = 5            # live ads per member at one time (team: no limit)
MAX_PICS = 12
SITE = "https://xpertcreation.com"
PAGE = "/var/www/xpertcreation-landing/wheels.html"
KD, FD, TD = dict(KINDS), dict(FUEL), dict(TRANS)


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
        notify(user, "wheels", text, link)
    except Exception:
        pass


def _admins(text, link="/wheels#team"):
    try:
        from notifications.views import notify_admins
        notify_admins("wheels", text, link)
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


def _name(u):
    return ((getattr(u, "full_name", "") or u.username or "Seller").strip())[:40]


def _featured():
    try:
        from shop.models import Order as SO
        now = timezone.now()
        return set(SO.objects.filter(product="wheels_boost", status="paid", starts_at__lte=now, ends_at__gt=now).values_list("target_id", flat=True))
    except Exception:
        return set()


def _title(a):
    return ("%s %s %s %d" % (a.make, a.model, a.version, a.year)).replace("  ", " ").strip()


def _pics(a):
    return ["/media/" + x for x in (a.images or [])]


def _a(a, full=False, fid=None):
    d = {"id": a.id, "kind": a.kind, "title": _title(a), "make": a.make, "model": a.model, "version": a.version, "year": a.year, "mileage": a.mileage,
         "fuel": a.fuel, "fuel_name": FD.get(a.fuel, a.fuel), "trans": a.trans, "trans_name": TD.get(a.trans, a.trans), "engine": a.engine, "price": a.price,
         "city": a.city, "area": a.area, "images": _pics(a), "status": a.status, "condition": a.condition, "assembly": a.assembly,
         "created": a.created_at.isoformat(), "featured": bool(fid and a.id in fid)}
    if full:
        d.update({"body": a.body, "color": a.color, "reg_city": a.reg_city, "features": a.features or [], "negotiable": a.negotiable, "desc": a.desc,
                  "whatsapp": a.whatsapp, "views": a.views, "seller": {"name": _name(a.user), "since": a.user.date_joined.year if getattr(a.user, "date_joined", None) else None,
                  "verified": _kyc(a.user), "ads": Ad.objects.filter(user=a.user, status="active").count()}})
    return d


def _guide(a):
    """A fair price range from similar ads (same make and model, year +/- 1) when there are at least 3."""
    qs = Ad.objects.filter(kind=a.kind, make__iexact=a.make, model__iexact=a.model, year__gte=a.year - 1, year__lte=a.year + 1,
                           status__in=("active", "sold")).exclude(pk=a.pk).values_list("price", flat=True)[:200]
    p = sorted(qs)
    if len(p) < 3:
        return None
    q = lambda f: p[min(len(p) - 1, max(0, int(round(f * (len(p) - 1)))))]
    return {"low": q(.25), "high": q(.75), "n": len(p)}


def _save_pic(f, oid):
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
    im.thumbnail((1400, 1400), Image.LANCZOS)
    rel = os.path.join("wheels", timezone.localdate().strftime("%Y%m"), "%d_%s.webp" % (oid, secrets.token_hex(6)))
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=80)
    return rel, None


def _rm(rel):
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
        me = {"id": u.pk, "name": _name(u), "phone": getattr(u, "whatsapp", "") or getattr(u, "phone", "") or "", "staff": _staff(u),
              "live": Ad.objects.filter(user=u, status="active").count(), "limit": None if _staff(u) else FREE_ADS}
    return Response({"kinds": KINDS, "makes": {k: {m: v for m, v in d.items()} for k, d in MAKES.items()}, "fuel": FUEL, "trans": TRANS, "body": BODY,
                     "features": FEATURES, "cities": CITIES, "me": me, "count": Ad.objects.filter(status="active").count()})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def ads(request):
    u = request.user
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in to post an ad.", 401)
        if not _staff(u) and Ad.objects.filter(user=u, status="active").count() >= FREE_ADS:
            return _err("You can have %d live ads at a time. Mark one as sold or pause it first." % FREE_ADS, 403)
        return _save(request, Ad(user=u))
    g = request.GET
    qs = Ad.objects.filter(status="active").select_related("user")
    if g.get("kind") in KD:
        qs = qs.filter(kind=g["kind"])
    for k in ("make", "model", "city"):
        v = _txt(g.get(k), 60)
        if v:
            qs = qs.filter(**{k + "__iexact": v})
    if g.get("fuel") in FD:
        qs = qs.filter(fuel=g["fuel"])
    if g.get("trans") in TD:
        qs = qs.filter(trans=g["trans"])
    if g.get("assembly") in ("local", "imported"):
        qs = qs.filter(assembly=g["assembly"])
    if g.get("condition") in ("used", "new"):
        qs = qs.filter(condition=g["condition"])
    for k, f, lo, hi in (("pmin", "price__gte", 0, 10 ** 10), ("pmax", "price__lte", 0, 10 ** 10), ("ymin", "year__gte", 1950, 2100), ("ymax", "year__lte", 1950, 2100),
                         ("kmax", "mileage__lte", 0, 10 ** 8)):
        v = _int(g.get(k), lo, hi)
        if v:
            qs = qs.filter(**{f: v})
    q = _txt(g.get("q"), 60)
    if q:
        for w in q.split()[:5]:
            qs = qs.filter(Q(make__icontains=w) | Q(model__icontains=w) | Q(version__icontains=w) | Q(city__icontains=w) | Q(year__icontains=w) | Q(color__icontains=w))
    if g.get("seller"):
        qs = qs.filter(user_id=_int(g.get("seller"), 1, 2 ** 62) or 0)
    sort = {"low": ["price"], "high": ["-price"], "km": ["mileage"], "year": ["-year", "-id"]}.get(g.get("sort"), ["-id"])
    fid = _featured()
    if fid and not g.get("sort"):
        from django.db.models import Case, IntegerField, Value, When
        qs = qs.annotate(fx=Case(When(pk__in=list(fid), then=Value(1)), default=Value(0), output_field=IntegerField()))
        sort = ["-fx"] + sort
    qs = qs.order_by(*sort)
    page = _int(g.get("page"), 1, 500) or 1
    total = qs.count()
    return Response({"total": total, "page": page, "pages": (total + 29) // 30, "ads": [_a(a, fid=fid) for a in qs[(page - 1) * 30: page * 30]]})


def _save(request, a):
    d = request.data
    kind = d.get("kind") if d.get("kind") in KD else "car"
    make, model, version = _txt(d.get("make"), 40), _txt(d.get("model"), 60), _txt(d.get("version"), 80)
    year, price = _int(d.get("year"), 1950, timezone.now().year + 1), _int(d.get("price"), 1000, 2 * 10 ** 9)
    km, cc = _int(d.get("mileage") or 0, 0, 5 * 10 ** 6), _int(d.get("engine") or 0, 0, 20000)
    city, phone = _txt(d.get("city"), 60), _phone(d.get("phone"))
    if not make or not model:
        return _err("Choose the make and model.")
    if not year:
        return _err("Give the model year.")
    if not price:
        return _err("Give the price in rupees (for example 2500000 for 25 lakh).")
    if km is None or cc is None:
        return _err("Check the mileage and engine numbers.")
    if not city or not phone:
        return _err("Give your city and a phone / WhatsApp number.")
    feats = [f for f in (d.get("features") if isinstance(d.get("features"), list) else []) if f in FEATURES[kind]][:40]
    a.kind, a.make, a.model, a.version, a.year, a.price, a.mileage, a.engine = kind, make, model, version, year, price, km, cc
    a.fuel = d.get("fuel") if d.get("fuel") in FD else "petrol"
    a.trans = d.get("trans") if d.get("trans") in TD else "manual"
    a.body = _txt(d.get("body"), 20) if _txt(d.get("body"), 20) in BODY[kind] else ""
    a.color, a.reg_city = _txt(d.get("color"), 30), _txt(d.get("reg_city"), 40)
    a.assembly = "imported" if d.get("assembly") == "imported" else "local"
    a.condition = "new" if d.get("condition") == "new" else "used"
    a.features, a.city, a.area, a.desc, a.phone = feats, city, _txt(d.get("area"), 80), _txt(d.get("desc"), 3000), phone
    a.negotiable, a.whatsapp = bool(d.get("negotiable", True)), bool(d.get("whatsapp", True))
    new = not a.pk
    a.save()
    if new:
        _notify(a.user, "Your ad %s is live on XpertWheels. Add photos so buyers trust it." % _title(a), "/wheels#edit-%d" % a.id)
    return Response(_a(a, True), status=201 if new else 200)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
def ad(request, pk):
    u = request.user
    a = Ad.objects.select_related("user").filter(pk=pk).first()
    own = bool(a and u.is_authenticated and a.user_id == u.pk)
    if not a or (a.status in ("hidden", "paused") and not (own or _staff(u))):
        return _err("This ad is not available.", 404)
    if request.method in ("POST", "DELETE"):
        if not own:
            return _err("Only the seller can change this ad.", 403)
        if request.method == "DELETE":
            for x in a.images or []:
                _rm(x)
            a.delete()
            return Response({"ok": True})
        if a.status == "hidden":
            return _err("This ad was taken down by our team: %s" % a.note, 403)
        return _save(request, a)
    if not own:
        Ad.objects.filter(pk=a.pk).update(views=F("views") + 1)
    d = _a(a, True, _featured())
    d["mine"] = own
    d["guide"] = _guide(a)
    d["more"] = [_a(x) for x in Ad.objects.filter(user=a.user, status="active").exclude(pk=a.pk)[:6]]
    d["similar"] = [_a(x) for x in Ad.objects.filter(status="active", kind=a.kind, make__iexact=a.make).exclude(user=a.user).order_by("-id")[:8]]
    if own:
        d.update({"phone": a.phone, "note": a.note, "calls": a.calls, "offers": a.offers.count()})
    return Response(d)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ad_image(request, pk):
    a = Ad.objects.filter(pk=pk, user=request.user).first()
    if not a:
        return _err("Only the seller can change the photos.", 403)
    pics = list(a.images or [])
    if request.data.get("remove") is not None:
        i = _int(request.data.get("remove"), 0, 30)
        if i is not None and i < len(pics):
            _rm(pics.pop(i))
    elif request.data.get("first") is not None:
        i = _int(request.data.get("first"), 0, 30)
        if i is not None and i < len(pics):
            pics.insert(0, pics.pop(i))
    else:
        if len(pics) >= MAX_PICS:
            return _err("An ad can have %d photos." % MAX_PICS)
        rel, e = _save_pic(request.FILES.get("file"), a.id)
        if e:
            return _err(e)
        pics.append(rel)
    a.images = pics; a.save(update_fields=["images"])
    return Response(_a(a, True))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def phone(request, pk):
    a = Ad.objects.filter(pk=pk, status__in=("active", "sold")).first()
    if not a:
        return _err("This ad is not available.", 404)
    if a.user_id != request.user.pk:
        Ad.objects.filter(pk=a.pk).update(calls=F("calls") + 1)
    wa = re.sub(r"\D", "", a.phone)
    if wa.startswith("0"):
        wa = "92" + wa[1:]
    return Response({"phone": a.phone, "whatsapp": wa if a.whatsapp else ""})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offer(request, pk):
    u, d = request.user, request.data
    a = Ad.objects.filter(pk=pk, status="active").select_related("user").first()
    if not a:
        return _err("This ad is not available.", 404)
    if a.user_id == u.pk:
        return _err("This is your own ad.")
    amt = _int(d.get("amount"), 1000, 2 * 10 ** 9)
    if not amt:
        return _err("Give your offer in rupees.")
    if Offer.objects.filter(ad=a, buyer=u, created_at__gte=timezone.now() - timedelta(hours=12)).count() >= 2:
        return _err("You already sent offers on this ad today. Wait for the seller to answer.")
    ph = _phone(d.get("phone"))
    o = Offer.objects.create(ad=a, buyer=u, amount=amt, message=_txt(d.get("message"), 300), phone=ph)
    _notify(a.user, "New offer Rs %s on your %s from %s" % ("{:,}".format(amt), _title(a), _name(u)), "/wheels#mine")
    return Response({"ok": True, "id": o.id}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def offer_reply(request, pk):
    o = Offer.objects.select_related("ad", "buyer").filter(pk=pk, ad__user=request.user).first()
    if not o:
        return _err("Offer not found.", 404)
    o.reply = _txt(request.data.get("text"), 300); o.save(update_fields=["reply"])
    _notify(o.buyer, "The seller of %s answered your offer: %s" % (_title(o.ad), o.reply[:80]), "/wheels#ad-%d" % o.ad_id)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report(request, pk):
    a = Ad.objects.filter(pk=pk).first()
    if not a:
        return _err("Not found.", 404)
    why = _txt(request.data.get("reason"), 300)
    if len(why) < 5:
        return _err("Tell us what is wrong.")
    if not Report.objects.filter(ad=a, user=request.user, done=False).exists():
        Report.objects.create(ad=a, user=request.user, reason=why)
        _admins("XpertWheels ad reported: %s - %s" % (_title(a), why[:80]))
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ad_act(request, pk, act):
    a = Ad.objects.filter(pk=pk, user=request.user).first()
    if not a or a.status == "hidden":
        return _err("Ad not found.", 404)
    if act == "sold":
        a.status, a.sold_at = "sold", timezone.now()
    elif act == "pause":
        a.status = "paused"
    elif act == "live":
        if a.status != "active" and not _staff(request.user) and Ad.objects.filter(user=request.user, status="active").count() >= FREE_ADS:
            return _err("You can have %d live ads at a time." % FREE_ADS, 403)
        a.status = "active"
    else:
        return _err("Unknown action.")
    a.save(update_fields=["status", "sold_at"])
    return Response(_a(a, True))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    u = request.user
    out = []
    for a in Ad.objects.filter(user=u).select_related("user")[:100]:
        d = _a(a)
        d.update({"views": a.views, "calls": a.calls, "note": a.note,
                  "offers": [{"id": o.id, "amount": o.amount, "message": o.message, "phone": o.phone, "reply": o.reply, "by": _name(o.buyer), "when": o.created_at.isoformat()}
                             for o in a.offers.select_related("buyer")[:30]]})
        out.append(d)
    return Response({"ads": out, "limit": None if _staff(u) else FREE_ADS})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    if not _staff(request.user):
        return _err("Team only.", 403)
    rep = Report.objects.filter(done=False).select_related("ad", "user")[:100]
    return Response({"reports": [{"id": r.id, "ad": _a(r.ad), "status": r.ad.status, "reason": r.reason, "by": _name(r.user), "when": r.created_at.isoformat()} for r in rep],
                     "recent": [dict(_a(a), seller=_name(a.user), status=a.status) for a in Ad.objects.select_related("user").order_by("-id")[:60]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_act(request, pk, act):
    if not _staff(request.user):
        return _err("Team only.", 403)
    if act == "done":
        Report.objects.filter(pk=pk).update(done=True)
        return Response({"ok": True})
    a = Ad.objects.filter(pk=pk).select_related("user").first()
    if not a:
        return _err("Not found.", 404)
    if act == "hide":
        a.status, a.note = "hidden", _txt(request.data.get("note"), 300) or "It breaks our rules."
        _notify(a.user, "Your ad %s was taken down: %s" % (_title(a), a.note), "/wheels#mine")
        Report.objects.filter(ad=a).update(done=True)
    elif act == "show":
        a.status, a.note = "active", ""
    else:
        return _err("Unknown action.")
    a.save(update_fields=["status", "note"])
    return Response({"ok": True})


def og(request, pk):
    """Link preview: the ad's photo, title and price on Facebook / WhatsApp."""
    try:
        page = open(PAGE, encoding="utf-8").read()
    except Exception:
        return HttpResponse("Not found", status=404)
    a = Ad.objects.filter(pk=pk, status__in=("active", "sold")).first()
    if a:
        title = "%s for sale - Rs %s | XpertWheels" % (_title(a), "{:,}".format(a.price))
        bits = ["%s km" % "{:,}".format(a.mileage) if a.kind != "bike" or a.mileage else "", FD.get(a.fuel, ""), TD.get(a.trans, "") if a.kind != "bike" else "",
                ("%d cc" % a.engine) if a.engine else "", a.city, "SOLD" if a.status == "sold" else ""]
        desc = " · ".join(b for b in bits if b) + (". " + re.sub(r"\s+", " ", a.desc)[:150] if a.desc else "")
        url = "%s/wheels?ad=%d" % (SITE, a.id)
        img = (SITE + "/media/" + a.images[0]) if a.images else SITE + "/brand/og/p/wheels.jpg"

        def setm(page, attr, key, val):
            pat = re.compile(r'(<meta %s="%s" content=")[^"]*(")' % (attr, re.escape(key)))
            return pat.sub(lambda m: m.group(1) + _h.escape(val, quote=True) + m.group(2), page, count=1)
        for attr, key, val in (("property", "og:title", title), ("name", "twitter:title", title), ("property", "og:description", desc),
                               ("name", "twitter:description", desc), ("name", "description", desc), ("property", "og:url", url),
                               ("property", "og:image", img), ("name", "twitter:image", img)):
            page = setm(page, attr, key, val)
        page = re.sub(r"<title>[^<]*</title>", lambda m: "<title>%s</title>" % _h.escape(title), page, count=1)
        page = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + url + m.group(2), page, count=1)
        if a.images:
            page = re.sub(r'<meta property="og:image:(?:width|height)" content="[^"]*">\n?', "", page)
    r = HttpResponse(page)
    r["Cache-Control"] = "public, max-age=300"
    return r
