"""Digital business cards: the owner's editor API, the public card, contact download, stats, old links."""
import html
import io
import json
import os
import re
import secrets

from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Sum
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Card, CardStat

MAX_CARDS = 3
SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{3,38})[a-z0-9]$")
RESERVED = {"admin", "api", "login", "cards", "card", "xpertcreation", "support", "help", "about", "static", "media"}
SITE = "https://xpertcreation.com"
LAND = "/var/www/xpertcreation-landing/"
SECTION_TYPES = {"about", "contact", "social", "links", "gallery", "hours", "video", "pdf", "meeting"}
CONNECT_TYPES = {"mobile", "whatsapp", "email", "sms", "website", "location", "phone"}


def _err(msg, code=400):
    return Response({"detail": msg}, status=code)


def _url(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p and not p.startswith("http") else (p or "")


def _t(v, n):
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", str(v or "")).strip()[:n]


def _link(v):
    v = _t(v, 400)
    if not v:
        return ""
    if re.match(r"^(javascript|data|vbscript):", v, re.I):
        return ""
    return v if re.match(r"^(https?://|mailto:|tel:)", v, re.I) else "https://" + v


def clean(d):
    """Only known fields, sensible lengths, safe links - whatever the browser sends."""
    d = d if isinstance(d, dict) else {}
    p = d.get("profile") if isinstance(d.get("profile"), dict) else {}
    out = {"profile": {"name": _t(p.get("name"), 80), "heading": _t(p.get("heading"), 80), "sub": _t(p.get("sub"), 80),
                       "photo": _t(p.get("photo"), 200), "logo": _t(p.get("logo"), 200), "bio": _t(p.get("bio"), 600)},
           "connect": [], "sections": [], "design": {}, "qr": {}}
    for c in (d.get("connect") or [])[:8]:
        if isinstance(c, dict) and c.get("type") in CONNECT_TYPES and _t(c.get("value"), 200):
            out["connect"].append({"type": c["type"], "value": _t(c.get("value"), 200)})
    for s in (d.get("sections") or [])[:14]:
        if not isinstance(s, dict) or s.get("type") not in SECTION_TYPES:
            continue
        t = s["type"]
        x = {"type": t, "on": s.get("on", True) is not False, "title": _t(s.get("title"), 60), "sub": _t(s.get("sub"), 120)}
        if t == "about":
            x["text"] = _t(s.get("text"), 2000)
        elif t == "contact":
            x.update({k: _t(s.get(k), 200) for k in ("phone", "email", "address", "company")})
        elif t in ("social", "links"):
            x["items"] = [{"label": _t(i.get("label"), 40), "url": _link(i.get("url")), "net": _t(i.get("net"), 20)}
                          for i in (s.get("items") or [])[:20] if isinstance(i, dict) and _link(i.get("url"))]
        elif t == "gallery":
            x["images"] = [_t(i, 200) for i in (s.get("images") or [])[:9] if _t(i, 200).startswith(("cards/", "/media/"))]
        elif t == "hours":
            x["days"] = [{"d": _t(i.get("d"), 12), "open": _t(i.get("open"), 5), "close": _t(i.get("close"), 5), "closed": bool(i.get("closed"))}
                         for i in (s.get("days") or [])[:7] if isinstance(i, dict)]
        elif t == "video":
            m = re.search(r"(?:youtu\.be/|v=|embed/|shorts/)([\w-]{11})", str(s.get("url") or ""))
            x["yt"] = m.group(1) if m else ""
        elif t == "meeting":
            x.update({"text": _t(s.get("text"), 400), "url": _link(s.get("url")), "button": _t(s.get("button"), 40)})
        elif t == "pdf":
            x["items"] = [{"label": _t(i.get("label"), 60), "url": _link(i.get("url"))} for i in (s.get("items") or [])[:10]
                          if isinstance(i, dict) and _link(i.get("url"))]
        out["sections"].append(x)
    dz = d.get("design") if isinstance(d.get("design"), dict) else {}
    col = lambda v, dflt: v if isinstance(v, str) and re.match(r"^#[0-9a-fA-F]{6}$", v) else dflt
    out["design"] = {"template": _t(dz.get("template"), 20) or "classic", "primary": col(dz.get("primary"), "#1B4DFF"),
                     "bg": col(dz.get("bg"), "#F4F6FB"), "text": col(dz.get("text"), "#0D1424"), "font": _t(dz.get("font"), 20) or "system",
                     "background": _t(dz.get("background"), 200), "shape": _t(dz.get("shape"), 12) or "rounded"}
    q = d.get("qr") if isinstance(d.get("qr"), dict) else {}
    out["qr"] = {"fg": col(q.get("fg"), "#0D1424"), "bg": col(q.get("bg"), "#FFFFFF"), "dots": _t(q.get("dots"), 12) or "square",
                 "eyes": _t(q.get("eyes"), 12) or "square", "logo": bool(q.get("logo")), "frame": _t(q.get("frame"), 24)}
    return out


def _stat(card, kind, label=""):
    row, _ = CardStat.objects.get_or_create(card=card, day=timezone.localdate(), kind=kind, label=label[:60])
    CardStat.objects.filter(pk=row.pk).update(count=F("count") + 1)


def _owner_out(c):
    return {"id": c.id, "slug": c.slug, "url": SITE + "/c/" + c.slug, "active": c.active, "hidden": c.hidden, "data": c.data,
            "views": c.views, "scans": c.scans, "saves": c.saves, "updated": timezone.localtime(c.updated_at).strftime("%d %b %Y")}


@api_view(["GET"])
@permission_classes([AllowAny])
def slug_check(request):
    s = str(request.GET.get("s") or "").lower().strip()
    if not SLUG.match(s) or s in RESERVED:
        return Response({"ok": False, "detail": "Use 5 to 40 letters, numbers or dashes."})
    return Response({"ok": not Card.objects.filter(slug=s).exists(), "detail": "" if not Card.objects.filter(slug=s).exists() else "That address is taken."})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def mine(request):
    if request.method == "GET":
        return Response({"cards": [_owner_out(c) for c in Card.objects.filter(owner=request.user).order_by("-updated_at")], "max": MAX_CARDS})
    if Card.objects.filter(owner=request.user).count() >= MAX_CARDS:
        return _err("You can have up to %d cards." % MAX_CARDS)
    s = str(request.data.get("slug") or "").lower().strip()
    if not SLUG.match(s) or s in RESERVED:
        return _err("Use 5 to 40 letters, numbers or dashes for the address.")
    if Card.objects.filter(slug=s).exists():
        return _err("That address is taken. Try another.")
    name = (getattr(request.user, "full_name", "") or "").strip()
    data = clean(request.data.get("data") or {"profile": {"name": name}, "connect": [{"type": "email", "value": request.user.email}] if request.user.email else [],
                                                "sections": [{"type": "about", "title": "About me", "text": ""}, {"type": "contact", "title": "Contact"}, {"type": "social", "title": "Follow me", "items": []}]})
    c = Card.objects.create(owner=request.user, slug=s, data=data)
    return Response(_owner_out(c), status=201)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def card(request, pk):
    c = Card.objects.filter(pk=pk, owner=request.user).first()
    if not c:
        return _err("Card not found.", 404)
    if request.method == "DELETE":
        c.delete(); return Response({"deleted": True})
    if request.method == "POST":
        if "data" in request.data:
            c.data = clean(request.data.get("data"))
        if "active" in request.data:
            c.active = str(request.data.get("active")).lower() in ("true", "1")
        c.save()
    out = _owner_out(c)
    days = list(CardStat.objects.filter(card=c, day__gte=timezone.localdate() - timezone.timedelta(days=29)).values("kind").annotate(n=Sum("count")))
    out["last30"] = {r["kind"]: r["n"] for r in days}
    out["clicks"] = list(CardStat.objects.filter(card=c, kind="click").values("label").annotate(n=Sum("count")).order_by("-n")[:12])
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def image(request, pk):
    """Profile photo, logo, gallery or background: resized, turned into WebP, stored under media/cards/."""
    c = Card.objects.filter(pk=pk, owner=request.user).first()
    f = request.FILES.get("image")
    if not c or not f:
        return _err("Pick a picture.")
    if f.size > 5 * 1024 * 1024:
        return _err("That picture is over 5 MB.")
    if not cache.add("cardimg:%d:%s" % (request.user.pk, timezone.now().strftime("%Y%m%d%H%M%S")), 1, 2):
        pass
    key = "cardimg:%d:%s" % (request.user.pk, timezone.localdate())
    n = cache.get(key, 0)
    if n >= 60:
        return _err("You have uploaded a lot of pictures today. Try again tomorrow.")
    cache.set(key, n + 1, 90000)
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); fmt = im.format; im.load()
    except Exception:
        return _err("That file is not a picture we can read.")
    if fmt not in ("JPEG", "PNG", "WEBP", "GIF"):
        return _err("Use a JPG, PNG or WebP picture.")
    kind = str(request.data.get("kind") or "gallery")
    size = {"photo": 800, "logo": 480, "background": 1400}.get(kind, 1280)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGBA") if kind == "logo" else im.convert("RGB")
    im.thumbnail((size, size))
    rel = "cards/%d/%s.webp" % (c.id, secrets.token_hex(10))
    full = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=82)
    return Response({"path": rel, "url": _url(rel)})


def _public(c):
    d = json.loads(json.dumps(c.data))
    p = d.get("profile", {})
    for k in ("photo", "logo"):
        p[k] = _url(p.get(k))
    d.setdefault("design", {})["background"] = _url(d.get("design", {}).get("background"))
    for s in d.get("sections", []):
        if s.get("type") == "gallery":
            s["images"] = [_url(i) for i in s.get("images", [])]
    d["sections"] = [s for s in d.get("sections", []) if s.get("on", True)]
    d["slug"] = c.slug
    d["url"] = SITE + "/c/" + c.slug
    return d


def _get_public(slug):
    c = Card.objects.filter(slug=slug).first()
    return c if c and c.active and not c.hidden else None


@api_view(["GET"])
@permission_classes([AllowAny])
def public(request, slug):
    c = _get_public(slug)
    if not c:
        return _err("This card is not available.", 404)
    if request.GET.get("count") == "1":
        vkey = "cardview:%d:%s" % (c.id, request.META.get("REMOTE_ADDR", ""))
        if cache.add(vkey, 1, 1800):
            if request.GET.get("src") == "qr":
                Card.objects.filter(pk=c.pk).update(scans=F("scans") + 1); _stat(c, "scan")
            else:
                Card.objects.filter(pk=c.pk).update(views=F("views") + 1); _stat(c, "view")
    return Response(_public(c))


def _vesc(s):
    return str(s).replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def vcf(request, slug):
    """'Add to contacts': a vCard with everything on the card."""
    c = _get_public(slug)
    if not c:
        return HttpResponse("Not found", status=404)
    d, p = c.data, c.data.get("profile", {})
    name = p.get("name") or c.slug
    parts = name.split(); last = parts.pop() if len(parts) > 1 else ""
    L = ["BEGIN:VCARD", "VERSION:3.0", "N:%s;%s;;;" % (_vesc(last), _vesc(" ".join(parts))), "FN:" + _vesc(name)]
    if p.get("sub"): L.append("ORG:" + _vesc(p["sub"]))
    if p.get("heading"): L.append("TITLE:" + _vesc(p["heading"]))
    for x in d.get("connect", []):
        v = x["value"]
        if x["type"] in ("mobile", "phone"): L.append("TEL;TYPE=CELL:" + re.sub(r"[^\d+]", "", v))
        elif x["type"] == "whatsapp":
            w = re.sub(r"\D", "", v); w = "92" + w[1:] if w.startswith("0") and len(w) == 11 else w
            L.append("item1.URL:https://wa.me/" + w); L.append("item1.X-ABLabel:WhatsApp")
        elif x["type"] == "email": L.append("EMAIL;TYPE=INTERNET:" + v)
        elif x["type"] == "website": L.append("URL:" + _link(v))
    for s in d.get("sections", []):
        if s.get("type") == "contact" and s.get("on", True):
            if s.get("phone"): L.append("TEL;TYPE=WORK:" + re.sub(r"[^\d+]", "", s["phone"]))
            if s.get("email"): L.append("EMAIL;TYPE=WORK:" + s["email"])
            if s.get("address"): L.append("ADR;TYPE=WORK:;;" + _vesc(s["address"]) + ";;;;")
    L.append("URL:" + SITE + "/c/" + c.slug)
    L.append("END:VCARD")
    Card.objects.filter(pk=c.pk).update(saves=F("saves") + 1); _stat(c, "save")
    r = HttpResponse("\r\n".join(L), content_type="text/vcard; charset=utf-8")
    r["Content-Disposition"] = 'attachment; filename="%s.vcf"' % re.sub(r"[^\w-]", "", c.slug)
    return r


@api_view(["POST"])
@permission_classes([AllowAny])
def click(request, slug):
    c = _get_public(slug)
    if c and cache.add("cardclick:%d:%s:%s" % (c.id, request.META.get("REMOTE_ADDR", ""), str(request.data.get("label"))[:30]), 1, 300):
        _stat(c, "click", _t(request.data.get("label"), 60))
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report(request, slug):
    c = Card.objects.filter(slug=slug).first()
    if not c:
        return _err("Not found.", 404)
    try:
        from notifications.views import notify_admins
        notify_admins("report", "Business card reported (%s): /c/%s" % (_t(request.data.get("reason"), 30) or "other", c.slug), "/admin/bizcards/card/%d/change/" % c.id)
    except Exception:
        pass
    return Response({"ok": True})


def page(request, slug):
    """/c/<slug>: the card page with its own title, description and picture for WhatsApp and Google."""
    try:
        src = open(LAND + "c.html", encoding="utf-8").read()
    except OSError:
        return HttpResponse("Not found", status=404)
    c = _get_public(slug)
    if not c:
        s = src.replace("</head>", '<meta name="robots" content="noindex">\n</head>', 1)
        return HttpResponse(s, status=404, content_type="text/html; charset=utf-8")
    p = c.data.get("profile", {})
    title = " \u2014 ".join(x for x in [p.get("name") or c.slug, p.get("heading"), p.get("sub")] if x)[:90]
    desc = (p.get("bio") or "Digital business card of %s. Save the contact, call or message in one tap." % (p.get("name") or c.slug))[:160]
    img = SITE + _url(p.get("photo")) if p.get("photo") else SITE + "/brand/og-cover.jpg"
    e = lambda v: html.escape(v, quote=True)
    s = re.sub(r"<title>.*?</title>", "<title>%s</title>" % e(title), src, 1, re.S)
    s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % e(desc), s, 1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">\s*', "", s)
    s = re.sub(r'<meta (?:property|name)="(?:og|twitter):[^"]*" content="[^"]*">\s*', "", s)
    head = ['<link rel="canonical" href="%s/c/%s">' % (SITE, c.slug), '<meta property="og:type" content="profile">',
            '<meta property="og:title" content="%s">' % e(title), '<meta property="og:description" content="%s">' % e(desc),
            '<meta property="og:image" content="%s">' % e(img), '<meta property="og:url" content="%s/c/%s">' % (SITE, c.slug),
            '<meta name="twitter:card" content="summary">']
    s = s.replace("</head>", "\n".join(head) + "\n</head>", 1)
    r = HttpResponse(s, content_type="text/html; charset=utf-8")
    r["Cache-Control"] = "public, max-age=120"
    return r


def legacy(request, token):
    """Old /card/<token> links and QR codes: send them to the new card."""
    c = Card.objects.filter(legacy_token=token).first()
    if c:
        return HttpResponsePermanentRedirect("/c/" + c.slug)
    return HttpResponsePermanentRedirect("/cards")
