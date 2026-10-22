"""XpertPros API (/api/pros/): hire a plumber, electrician, AC technician, cleaner and more.
meta/                    categories, cities, me (am I a pro, ID check done?)
list/?cat=&city=&q=      find pros (featured first, then rating)
p/<id>/                  one pro: profile, work photos, reviews; signed in: phone / WhatsApp
me/                      GET / POST my pro profile (ID-verified members only); me/photo/ add / remove a work photo
jobs/                    GET my jobs (as a customer) | POST a new job (pro=<id> to book one pro directly)
jobs/<id>/               GET one job with its offers (customer, or a pro who can see it)
jobs/<id>/photo/         customer: add a photo of the problem
jobs/<id>/<act>/         customer: cancel, done, review (stars, text), hire (offer=<id>)
                         pro: offer (price, note), decline (a direct booking), withdraw, done
feed/                    pro: open jobs in my city and services + direct bookings + my hired jobs
offers/<id>/             (kept for links) GET one offer
report/                  report a pro or a job -> team bell
reviews/<id>/reply/      pro: answer a review
team/                    moderators: reports, latest pros and jobs; team/<kind>/<id>/<act>/  pause | live | hide | done
og/<id>/                 link preview for xpertcreation.com/pros?p=<id>"""
import html as _h
import os
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .data import CATKEYS, CATS, CITIES, WHEN
from .models import Job, Offer, Pro, Report, Review

SITE = "https://xpertcreation.com"
PAGE = "/var/www/xpertcreation-landing/pros.html"
CD = {c[0]: c for c in CATS}
MAX_PICS, OPEN_JOBS, OPEN_DAYS = 8, 5, 7


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
        notify(user, "pros", text, link)
    except Exception:
        pass


def _admins(text, link="/pros#team"):
    try:
        from notifications.views import notify_admins
        notify_admins("pros", text, link)
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
    return _staff(u)


def _mypro(u):
    return Pro.objects.filter(user=u).first() if u and u.is_authenticated else None


def _maplink(v):
    v = _txt(v, 300)
    if not v:
        return ""
    if re.match(r"^-?\d{1,2}\.\d+\s*,\s*-?\d{1,3}\.\d+$", v):
        return "https://www.google.com/maps?q=" + v.replace(" ", "")
    return v if re.match(r"^https://(www\.)?(google\.[a-z.]+/maps|maps\.google\.[a-z.]+|maps\.app\.goo\.gl|goo\.gl/maps)", v) else ""


def _featured():
    try:
        from shop.models import Order as SO
        now = timezone.now()
        return set(SO.objects.filter(product="pro_boost", status="paid", starts_at__lte=now, ends_at__gt=now).values_list("target_id", flat=True))
    except Exception:
        return set()


def _avatar(u):
    a = getattr(u, "avatar", "") or ""
    a = str(a)
    return a if (not a or a.startswith(("http", "/"))) else "/media/" + a


def _cat(k):
    c = CD.get(k) or CD["other"]
    return {"key": c[0], "name": c[1], "ur": c[2], "e": c[3]}


def _p(p, fid=None, full=False, viewer=None):
    d = {"id": p.id, "name": p.name, "services": [_cat(k) for k in p.services or [] if k in CD], "city": p.city, "areas": p.areas, "years": p.years,
         "rate": p.rate, "available": p.available, "verified": True, "photo": _avatar(p.user), "rating": round(p.rating_sum / p.rating_n, 1) if p.rating_n else None,
         "reviews": p.rating_n, "jobs_done": p.jobs_done, "featured": bool(fid and p.id in fid), "since": p.created_at.year,
         "pics": ["/media/" + x for x in (p.photos or [])][:1]}
    if full:
        d.update({"about": p.about, "pics": ["/media/" + x for x in (p.photos or [])],
                  "review_list": [{"id": r.id, "stars": r.stars, "text": r.text, "reply": r.reply, "by": ((getattr(r.customer, "full_name", "") or "Customer").split() or ["Customer"])[0],
                                   "when": r.created_at.isoformat(), "job": _cat(r.job.category)["name"]} for r in p.reviews.select_related("customer", "job").order_by("-id")[:30]]})
        if viewer and viewer.is_authenticated:
            d.update({"phone": p.phone, "whatsapp": p.whatsapp or p.phone})
    return d


def _job_out(j, u):
    mine = u.is_authenticated and j.customer_id == u.id
    pro = _mypro(u)
    hired = bool(pro and j.pro_id == pro.id and j.status in ("hired", "done"))
    d = {"id": j.id, "category": _cat(j.category), "title": j.title, "details": j.details, "city": j.city, "area": j.area, "when": j.when,
         "when_name": dict(WHEN).get(j.when, ""), "date": j.date.isoformat() if j.date else None, "budget": j.budget, "photos": ["/media/" + x for x in (j.photos or [])],
         "status": j.status, "direct": j.direct, "created": j.created_at.isoformat(), "price": j.price, "mine": mine,
         "customer": ((getattr(j.customer, "full_name", "") or "Customer").split() or ["Customer"])[0]}
    if mine:
        d["offers"] = [{"id": o.id, "price": o.price, "note": o.note, "status": o.status, "when": o.created_at.isoformat(), "pro": _p(o.pro)}
                       for o in j.offers.select_related("pro", "pro__user").exclude(status="withdrawn").order_by("price", "id")]
        d["phone"], d["address"], d["maplink"] = j.phone, j.address, j.maplink
        if j.pro_id:
            d["hired"] = dict(_p(j.pro), phone=j.pro.phone, whatsapp=j.pro.whatsapp or j.pro.phone)
        d["reviewed"] = hasattr(j, "review")
    if pro:
        o = j.offers.filter(pro=pro).first()
        d["my_offer"] = {"id": o.id, "price": o.price, "note": o.note, "status": o.status} if o else None
        d["offers_n"] = j.offers.exclude(status="withdrawn").count()
        if hired:      # the hired pro gets the address and phone
            d.update({"phone": j.phone, "address": j.address, "maplink": j.maplink, "hired_me": True})
    return d


def _save_pic(f, kind, oid):
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
    rel = os.path.join("pros", timezone.localdate().strftime("%Y%m"), "%s%d_%s.webp" % (kind, oid, secrets.token_hex(6)))
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=80)
    return rel, None


def _rm(rel):
    try:
        os.remove(os.path.join(str(settings.MEDIA_ROOT), rel))
    except OSError:
        pass


def _expire():
    Job.objects.filter(status="open", created_at__lt=timezone.now() - timedelta(days=OPEN_DAYS)).update(status="expired")


# ---------------------------------------------------------------- browse
@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    u = request.user
    me = None
    if u.is_authenticated:
        p = Pro.objects.filter(user=u).first()
        me = {"pro": _p(p) if p else None, "kyc": _kyc(u), "name": (getattr(u, "full_name", "") or "").strip(), "phone": getattr(u, "whatsapp", "") or getattr(u, "phone", "") or ""}
    counts = {}
    for p in Pro.objects.filter(status="active").values_list("services", flat=True):
        for k in p or []:
            counts[k] = counts.get(k, 0) + 1
    return Response({"cats": [dict(_cat(k), pros=counts.get(k, 0)) for k in CATKEYS], "cities": CITIES, "when": WHEN, "me": me,
                     "total": Pro.objects.filter(status="active").count()})


@api_view(["GET"])
@permission_classes([AllowAny])
def plist(request):
    g = request.GET
    qs = Pro.objects.filter(status="active").select_related("user")
    cat, city, q = g.get("cat", ""), _txt(g.get("city"), 60), _txt(g.get("q"), 60)
    if city:
        qs = qs.filter(city__iexact=city)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(about__icontains=q) | Q(areas__icontains=q))
    rows = list(qs.order_by("-id")[:600])
    if cat in CD:
        rows = [p for p in rows if cat in (p.services or [])]
    fid = _featured()
    rows.sort(key=lambda p: (p.id not in fid, not p.available, -(p.rating_sum / p.rating_n if p.rating_n else 0), -p.jobs_done, -p.id))
    page = _int(g.get("page"), 1, 100) or 1
    return Response({"pros": [_p(p, fid) for p in rows[(page - 1) * 24: page * 24]], "total": len(rows), "page": page})


@api_view(["GET"])
@permission_classes([AllowAny])
def pro_page(request, pk):
    p = Pro.objects.select_related("user").filter(pk=pk).first()
    if not p or (p.status != "active" and not (_staff(request.user) or p.user_id == request.user.id)):
        return _err("This pro is not available.", 404)
    return Response(_p(p, _featured(), True, request.user))


# ---------------------------------------------------------------- my pro profile
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def me(request):
    u, d = request.user, request.data
    p = Pro.objects.filter(user=u).first()
    if request.method == "POST":
        if not _kyc(u):
            return _err("Only ID-verified members can work as a pro (customers let you into their homes). Get verified first: xpertcreation.com/get-verified", 403)
        if p and p.status == "paused":
            return _err("Your pro profile is paused by our team: %s" % (p.note or "contact support."), 403)
        name, city, phone = _txt(d.get("name"), 80), _txt(d.get("city"), 60), _phone(d.get("phone"))
        sv = [k for k in (d.get("services") or []) if k in CD][:6]
        if len(name) < 3 or not city or not phone:
            return _err("Give your name, city and a phone number.")
        if not sv:
            return _err("Choose at least one service you do.")
        new = p is None
        p = p or Pro(user=u)
        p.name, p.city, p.phone, p.services = name, city, phone, sv
        p.whatsapp, p.areas, p.about, p.rate = _phone(d.get("whatsapp")), _txt(d.get("areas"), 200), _txt(d.get("about"), 2000), _txt(d.get("rate"), 80)
        p.years = _int(d.get("years"), 0, 60) or 0
        p.available = bool(d.get("available", True))
        p.save()
        if new:
            _admins("New pro on XpertPros: %s (%s, %s)" % (p.name, ", ".join(CD[k][1] for k in sv), p.city))
            _notify(u, "\U0001F6E0️ You are now on XpertPros. Customers in %s can find and book you. Turn on notifications so you see new jobs fast." % p.city, "/pros#work")
    return Response({"pro": _p(p, None, True, u) if p else None, "kyc": _kyc(u)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def me_photo(request):
    p = Pro.objects.filter(user=request.user).first()
    if not p:
        return _err("Make your pro profile first.", 403)
    rm = _int(request.data.get("remove"), 0, 50)
    if rm is not None:
        if rm < len(p.photos or []):
            _rm(p.photos[rm]); p.photos = [x for i, x in enumerate(p.photos) if i != rm]; p.save(update_fields=["photos"])
        return Response(_p(p, None, True, request.user))
    if len(p.photos or []) >= MAX_PICS:
        return _err("Up to %d work photos." % MAX_PICS)
    rel, e = _save_pic(request.FILES.get("file"), "w", p.id)
    if e:
        return _err(e)
    p.photos = (p.photos or []) + [rel]; p.save(update_fields=["photos"])
    return Response(_p(p, None, True, request.user))


# ---------------------------------------------------------------- jobs (customer)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def jobs(request):
    u, d = request.user, request.data
    _expire()
    if request.method == "GET":
        return Response({"jobs": [_job_out(j, u) for j in Job.objects.filter(customer=u).select_related("pro", "customer").order_by("-id")[:60]]})
    if Job.objects.filter(customer=u, status="open").count() >= OPEN_JOBS:
        return _err("You already have %d open jobs. Close or cancel one first." % OPEN_JOBS)
    cat = d.get("category") if d.get("category") in CD else None
    title, city, phone = _txt(d.get("title"), 120), _txt(d.get("city"), 60), _phone(d.get("phone"))
    if not cat:
        return _err("Choose what kind of work you need.")
    if len(title) < 5:
        return _err("Say in a few words what you need (like: Kitchen tap is leaking).")
    if not city or not phone:
        return _err("Give your city and a phone number. Only the pro you hire sees your number.")
    when = d.get("when") if d.get("when") in dict(WHEN) else "asap"
    day = None
    if when == "date":
        try:
            from datetime import date
            day = date.fromisoformat(str(d.get("date"))[:10])
        except Exception:
            return _err("Choose the date.")
    pro = None
    if d.get("pro"):
        pro = Pro.objects.filter(pk=_int(d.get("pro"), 1, 2 ** 62) or 0, status="active").first()
        if not pro:
            return _err("That pro is not available right now.")
        if pro.user_id == u.id:
            return _err("You can't book yourself.")
    j = Job.objects.create(customer=u, category=cat, title=title, details=_txt(d.get("details"), 2000), city=city, area=_txt(d.get("area"), 120),
                           address=_txt(d.get("address"), 240), maplink=_maplink(d.get("maplink")), phone=phone, when=when, date=day,
                           budget=_int(d.get("budget"), 0, 10 ** 8) or 0, direct=bool(pro), pro=pro)
    label = "%s %s" % (CD[cat][3], CD[cat][1])
    if pro:
        _notify(pro.user, "\U0001F4E9 New booking for you: %s - \"%s\" in %s. Send your price or say no." % (label, title, j.area or city), "/pros#job-%d" % j.id)
    else:
        n = 0
        for p in Pro.objects.filter(status="active", available=True, city__iexact=city).exclude(user=u).select_related("user")[:400]:
            if cat in (p.services or []):
                _notify(p.user, "\U0001F6E0️ New job near you: %s - \"%s\" in %s. Send your price." % (label, title, j.area or city), "/pros#job-%d" % j.id)
                n += 1
    return Response(_job_out(j, u), status=201)


def _can_see(j, u):
    if j.customer_id == u.id or _staff(u):
        return True
    p = _mypro(u)
    if not p or p.status != "active":
        return False
    if j.direct:
        return j.pro_id == p.id
    return (j.pro_id == p.id) or (j.status == "open" and j.city.lower() == p.city.lower() and j.category in (p.services or [])) or j.offers.filter(pro=p).exists()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def job(request, pk):
    j = Job.objects.select_related("customer", "pro", "pro__user").filter(pk=pk).first()
    if not j or not _can_see(j, request.user):
        return _err("Job not found.", 404)
    return Response(_job_out(j, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def job_photo(request, pk):
    j = Job.objects.filter(pk=pk, customer=request.user).first()
    if not j:
        return _err("Job not found.", 404)
    if len(j.photos or []) >= 4:
        return _err("Up to 4 photos.")
    rel, e = _save_pic(request.FILES.get("file"), "j", j.id)
    if e:
        return _err(e)
    j.photos = (j.photos or []) + [rel]; j.save(update_fields=["photos"])
    return Response(_job_out(j, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def job_act(request, pk, act):
    u, d = request.user, request.data
    j = Job.objects.select_related("customer", "pro", "pro__user").filter(pk=pk).first()
    if not j or not _can_see(j, u):
        return _err("Job not found.", 404)
    pro = _mypro(u)
    label = CD.get(j.category, CD["other"])[1]
    # ---- customer
    if j.customer_id == u.id:
        if act == "cancel":
            if j.status not in ("open", "hired"):
                return _err("This job is already closed.")
            if j.pro_id and j.status == "hired":
                _notify(j.pro.user, "The customer cancelled the job \"%s\"." % j.title, "/pros#job-%d" % j.id)
            j.status = "cancelled"; j.save(update_fields=["status"])
            j.offers.filter(status="sent").update(status="declined")
        elif act == "hire":
            o = j.offers.select_related("pro", "pro__user").filter(pk=_int(d.get("offer"), 1, 2 ** 62) or 0, status="sent").first()
            if j.status != "open" or not o:
                return _err("That price is not open any more.")
            with transaction.atomic():
                j.pro, j.price, j.status, j.hired_at = o.pro, o.price, "hired", timezone.now()
                j.save(update_fields=["pro", "price", "status", "hired_at"])
                o.status = "accepted"; o.save(update_fields=["status"])
                for x in j.offers.select_related("pro__user").filter(status="sent").exclude(pk=o.pk):
                    x.status = "declined"; x.save(update_fields=["status"])
                    _notify(x.pro.user, "The customer chose another pro for \"%s\". Keep going, more jobs are coming!" % j.title, "/pros#work")
            _notify(o.pro.user, "✅ You are hired: \"%s\" (%s)%s. Open the job to see the address and phone." % (j.title, label, (" for Rs %s" % "{:,}".format(o.price)) if o.price else ""), "/pros#job-%d" % j.id)
        elif act == "done":
            if j.status != "hired":
                return _err("Hire a pro first.")
            _finish(j)
        elif act == "review":
            if j.status != "done" or not j.pro_id:
                return _err("You can review once the work is done.")
            if hasattr(j, "review"):
                return _err("You already reviewed this job.")
            s = _int(d.get("stars"), 1, 5)
            if not s:
                return _err("Choose 1 to 5 stars.")
            Review.objects.create(job=j, pro=j.pro, customer=u, stars=s, text=_txt(d.get("text"), 500))
            Pro.objects.filter(pk=j.pro_id).update(rating_sum=F("rating_sum") + s, rating_n=F("rating_n") + 1)
            _notify(j.pro.user, "⭐ New review: %d star%s for \"%s\"." % (s, "" if s == 1 else "s", j.title), "/pros?p=%d" % j.pro_id)
        else:
            return _err("Unknown action.")
        j.refresh_from_db()
        return Response(_job_out(j, u))
    # ---- pro
    if not pro or pro.status != "active":
        return _err("Only pros can do that.", 403)
    if act == "offer":
        if j.status != "open" or (j.direct and j.pro_id != pro.id):
            return _err("This job is not open any more.")
        price = _int(d.get("price") or 0, 0, 10 ** 8)
        if price is None:
            return _err("Write your price in rupees, or 0 if you need to see the work first.")
        note = _txt(d.get("note"), 400)
        o, created = Offer.objects.get_or_create(job=j, pro=pro, defaults={"price": price, "note": note})
        if not created:
            if o.status not in ("sent", "withdrawn"):
                return _err("You can't change this price now.")
            o.price, o.note, o.status = price, note, "sent"; o.save(update_fields=["price", "note", "status"])
        if j.direct:       # a direct booking: the pro accepts with a price -> hired straight away
            with transaction.atomic():
                o.status = "accepted"; o.save(update_fields=["status"])
                j.price, j.status, j.hired_at = price, "hired", timezone.now(); j.save(update_fields=["price", "status", "hired_at"])
            _notify(j.customer, "✅ %s accepted your booking \"%s\"%s. You can call or WhatsApp them now." % (pro.name, j.title, (" for Rs %s" % "{:,}".format(price)) if price else ""), "/pros#job-%d" % j.id)
        elif created or o.status == "sent":
            _notify(j.customer, "\U0001F4B0 %s sent a price for \"%s\": %s. Compare and hire." % (pro.name, j.title, ("Rs %s" % "{:,}".format(price)) if price else "after seeing the work"), "/pros#job-%d" % j.id)
    elif act == "decline":
        if not j.direct or j.pro_id != pro.id or j.status != "open":
            return _err("Nothing to decline.")
        j.status, j.pro = "open", None
        j.direct = False; j.save(update_fields=["status", "pro", "direct"])
        _notify(j.customer, "%s can't take \"%s\" right now. We opened it to all %s pros in %s, so you'll get prices soon." % (pro.name, j.title, label.lower(), j.city), "/pros#job-%d" % j.id)
        for p in Pro.objects.filter(status="active", available=True, city__iexact=j.city).exclude(pk=pro.pk).exclude(user=j.customer).select_related("user")[:400]:
            if j.category in (p.services or []):
                _notify(p.user, "\U0001F6E0️ New job near you: \"%s\" in %s. Send your price." % (j.title, j.area or j.city), "/pros#job-%d" % j.id)
    elif act == "withdraw":
        n = Offer.objects.filter(job=j, pro=pro, status="sent").update(status="withdrawn")
        if not n:
            return _err("No open price to take back.")
    elif act == "done":
        if j.status != "hired" or j.pro_id != pro.id:
            return _err("This job is not yours.")
        _finish(j)
        _notify(j.customer, "%s marked \"%s\" as done. Please leave a review, it helps other customers." % (pro.name, j.title), "/pros#job-%d" % j.id)
    else:
        return _err("Unknown action.")
    j.refresh_from_db()
    return Response(_job_out(j, u))


def _finish(j):
    if j.status == "done":
        return
    j.status, j.done_at = "done", timezone.now(); j.save(update_fields=["status", "done_at"])
    Pro.objects.filter(pk=j.pro_id).update(jobs_done=F("jobs_done") + 1)


# ---------------------------------------------------------------- pro work feed
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def feed(request):
    u = request.user
    p = Pro.objects.filter(user=u).first()
    if not p:
        return Response({"pro": None, "kyc": _kyc(u), "open": [], "booked": [], "hired": [], "offered": []})
    _expire()
    base = Job.objects.select_related("customer", "pro").exclude(customer=u)
    open_ = [j for j in base.filter(status="open", direct=False, city__iexact=p.city).order_by("-id")[:200] if j.category in (p.services or [])]
    return Response({"pro": _p(p, None, True, u), "kyc": _kyc(u),
                     "booked": [_job_out(j, u) for j in base.filter(status="open", direct=True, pro=p).order_by("-id")[:50]],
                     "open": [_job_out(j, u) for j in open_[:60]],
                     "hired": [_job_out(j, u) for j in base.filter(pro=p, status__in=("hired", "done")).order_by("-id")[:60]],
                     "offered": [_job_out(o.job, u) for o in Offer.objects.select_related("job", "job__customer", "job__pro").filter(pro=p, status="sent", job__status="open").order_by("-id")[:60]]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def offer_act(request, pk):
    o = Offer.objects.select_related("job").filter(pk=pk).first()
    if not o or not _can_see(o.job, request.user):
        return _err("Not found.", 404)
    return Response(_job_out(o.job, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report(request):
    d = request.data
    reason = _txt(d.get("reason"), 300)
    if len(reason) < 5:
        return _err("Tell us what is wrong.")
    p = Pro.objects.filter(pk=_int(d.get("pro"), 1, 2 ** 62) or 0).first()
    j = Job.objects.filter(pk=_int(d.get("job"), 1, 2 ** 62) or 0).first()
    if j and not _can_see(j, request.user):
        j = None
    if not p and not j:
        return _err("Nothing to report.")
    Report.objects.create(by=request.user, pro=p, job=j, reason=reason)
    _admins("XpertPros report: %s - %s" % (p.name if p else "job #%d" % j.id, reason[:80]))
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review_reply(request, pk):
    r = Review.objects.filter(pk=pk, pro__user=request.user).first()
    if not r:
        return _err("Review not found.", 404)
    r.reply = _txt(request.data.get("text"), 500); r.save(update_fields=["reply"])
    return Response({"ok": True})


# ---------------------------------------------------------------- team
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team(request):
    if not _staff(request.user):
        return _err("Team only.", 403)
    return Response({"reports": [{"id": r.id, "reason": r.reason, "pro": _p(r.pro) if r.pro else None, "job": r.job_id, "when": r.created_at.isoformat()}
                                 for r in Report.objects.select_related("pro", "pro__user").filter(done=False).order_by("-id")[:100]],
                     "pros": [dict(_p(p), status=p.status, note=p.note, phone=p.phone) for p in Pro.objects.select_related("user").order_by("-id")[:100]],
                     "jobs": [{"id": j.id, "title": j.title, "city": j.city, "status": j.status, "category": _cat(j.category)["name"], "when": j.created_at.isoformat()}
                              for j in Job.objects.order_by("-id")[:100]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_act(request, kind, pk, act):
    if not _staff(request.user):
        return _err("Team only.", 403)
    note = _txt(request.data.get("note"), 300)
    if kind == "pro":
        p = Pro.objects.select_related("user").filter(pk=pk).first()
        if not p or act not in ("pause", "live"):
            return _err("Not found.", 404)
        p.status, p.note = ("paused", note or "Paused by our team.") if act == "pause" else ("active", "")
        p.save(update_fields=["status", "note"])
        _notify(p.user, ("Your XpertPros profile was paused: %s" % p.note) if act == "pause" else "Your XpertPros profile is live again.", "/pros#work")
    elif kind == "job":
        j = Job.objects.filter(pk=pk).first()
        if not j or act != "hide":
            return _err("Not found.", 404)
        j.status = "cancelled"; j.save(update_fields=["status"])
    elif kind == "report":
        Report.objects.filter(pk=pk).update(done=True)
    else:
        return _err("Unknown.")
    return Response({"ok": True})


def og(request, pk):
    """Link preview for a pro: photo, name, services, city and rating."""
    try:
        page = open(PAGE, encoding="utf-8").read()
    except Exception:
        return HttpResponse("Not found", status=404)
    p = Pro.objects.select_related("user").filter(pk=pk, status="active").first()
    if p:
        sv = ", ".join(CD[k][1] for k in (p.services or []) if k in CD)
        title = "%s - %s in %s | XpertPros" % (p.name, sv, p.city)
        rt = (" · %.1f★ (%d reviews)" % (p.rating_sum / p.rating_n, p.rating_n)) if p.rating_n else ""
        desc = ("ID-verified %s in %s%s. %s" % (sv.lower(), p.city, rt, re.sub(r"\s+", " ", p.about)[:150])).strip()
        url = "%s/pros?p=%d" % (SITE, p.id)
        img = (SITE + "/media/" + p.photos[0]) if p.photos else (SITE + _avatar(p.user) if _avatar(p.user).startswith("/") else SITE + "/brand/og/p/pros.jpg")

        def setm(page, attr, key, val):
            pat = re.compile(r'(<meta %s="%s" content=")[^"]*(")' % (attr, re.escape(key)))
            return pat.sub(lambda m: m.group(1) + _h.escape(val, quote=True) + m.group(2), page, count=1)
        for attr, key, val in (("property", "og:title", title), ("name", "twitter:title", title), ("property", "og:description", desc),
                               ("name", "twitter:description", desc), ("name", "description", desc), ("property", "og:url", url),
                               ("property", "og:image", img), ("name", "twitter:image", img)):
            page = setm(page, attr, key, val)
        page = re.sub(r"<title>[^<]*</title>", lambda m: "<title>%s</title>" % _h.escape(title), page, count=1)
        page = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + url + m.group(2), page, count=1)
        page = re.sub(r'<meta property="og:image:(?:width|height)" content="[^"]*">\n?', "", page)
    r = HttpResponse(page)
    r["Cache-Control"] = "public, max-age=300"
    return r
