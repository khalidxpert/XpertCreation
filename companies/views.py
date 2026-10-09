"""Company pages: the owner's editor (details, logo/cover, website first, then KYC), the moderators' review,
the public page /company/<slug>, posts, search (for check-ins) and private KYC documents."""
import html
import os
import re
import secrets

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Company, CompanyDoc

SITE = "https://xpertcreation.com"
LAND = "/var/www/xpertcreation-landing/"
DOCS = os.environ.get("XC_KYC_DIR", "/var/lib/gunicorn-academy/kyc_docs")
MAX_COMPANIES = 3
SIZES = ["1-10", "11-50", "51-200", "201-1000", "1000+"]
PHONE = re.compile(r"^\+?\d{10,15}$")
EDIT = ["tagline", "about", "industry", "size", "founded", "city", "country", "address", "website", "email", "phone", "whatsapp"]


def _err(m, code=400):
    return Response({"detail": m}, status=code)


def _reviewer(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _media(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p and not p.startswith(("http", "/")) else (p or "")


def _t(v, n):
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", str(v or "")).strip()[:n]


def public_ok(c):
    """Shown to everyone once the website is verified (step 1) or KYC is approved."""
    return not c.hidden and (bool(c.domain_verified_at) or c.status == Company.APPROVED)


def _out(c, full=False):
    d = {"id": c.id, "slug": c.slug, "name": c.name, "tagline": c.tagline, "about": c.about, "industry": c.industry, "size": c.size,
         "founded": c.founded, "city": c.city, "country": c.country, "address": c.address, "website": c.website, "email": c.email, "phone": c.phone,
         "logo": _media(c.logo), "cover": _media(c.cover), "verified": c.status == Company.APPROVED, "website_verified": bool(c.domain_verified_at),
         "domain": c.domain if c.domain_verified_at else "", "url": SITE + "/company/" + c.slug}
    if full:
        d.update({"whatsapp": c.whatsapp, "status": c.status, "status_label": dict(Company.STATES)[c.status], "review_note": c.review_note,
                  "domain_pending": c.domain, "domain_token": c.domain_token, "public": public_ok(c),
                  "docs": [{"id": x.id, "kind": x.kind, "kind_label": dict(CompanyDoc.KINDS)[x.kind], "name": x.name, "size": x.size,
                            "when": timezone.localtime(x.uploaded_at).strftime("%d %b %Y")} for x in c.docs.order_by("id")]})
    return d


def _unique_slug(name):
    base = slugify(name)[:50] or "company"
    s, i = base, 2
    while Company.objects.filter(slug=s).exists() or s in ("new", "manage", "review"):
        s = "%s-%d" % (base, i); i += 1
    return s


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def mine(request):
    if request.method == "GET":
        return Response({"companies": [_out(c, True) for c in Company.objects.filter(owner=request.user).order_by("id")], "max": MAX_COMPANIES})
    name = _t(request.data.get("name"), 120)
    if len(name) < 2:
        return _err("Enter the company's name.")
    if Company.objects.filter(owner=request.user).count() >= MAX_COMPANIES:
        return _err("You can manage up to %d companies." % MAX_COMPANIES)
    if Company.objects.filter(name__iexact=name, status=Company.APPROVED).exists():
        return _err("A verified company with this name is already on XpertConnect. If it is yours, contact support.")
    c = Company.objects.create(owner=request.user, name=name, slug=_unique_slug(name))
    return Response(_out(c, True), status=201)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def company(request, pk):
    c = Company.objects.filter(pk=pk, owner=request.user).first()
    if not c:
        return _err("Company not found.", 404)
    if request.method == "DELETE":
        _wipe_docs(c); c.delete(); return Response({"deleted": True})
    if request.method == "POST":
        d = request.data
        if "name" in d and c.status != Company.APPROVED:          # a verified company's name only changes through support
            nm = _t(d.get("name"), 120)
            if len(nm) >= 2: c.name = nm
        for f in EDIT:
            if f in d:
                v = d.get(f)
                if f == "founded":
                    try:
                        v = int(v) if v not in ("", None) else None
                    except (TypeError, ValueError):
                        v = None
                    c.founded = v if v is None or 1800 <= v <= timezone.now().year else c.founded
                elif f == "size":
                    c.size = v if v in SIZES else ""
                elif f == "country":
                    c.country = _t(v, 2).upper()
                elif f in ("phone", "whatsapp"):
                    v = re.sub(r"[\s-]", "", _t(v, 24))
                    if v and not PHONE.match(v):
                        return _err("Write the %s number like +923001234567." % ("WhatsApp" if f == "whatsapp" else "phone"))
                    setattr(c, f, v)
                elif f == "website":
                    v = _t(v, 200)
                    if v and not re.match(r"^https?://", v, re.I): v = "https://" + v
                    c.website = v
                elif f == "about":
                    c.about = _t(v, 4000)
                else:
                    setattr(c, f, _t(v, {"tagline": 160, "industry": 80, "city": 80, "address": 240, "email": 120}.get(f, 120)))
        c.save()
    return Response(_out(c, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def image(request, pk):
    c = Company.objects.filter(pk=pk, owner=request.user).first()
    f = request.FILES.get("image")
    if not c or not f:
        return _err("Pick a picture.")
    if f.size > 5 * 1024 * 1024:
        return _err("That picture is over 5 MB.")
    from PIL import Image, ImageOps
    try:
        im = Image.open(f); fmt = im.format; im.load()
    except Exception:
        return _err("That file is not a picture we can read.")
    if fmt not in ("JPEG", "PNG", "WEBP"):
        return _err("Use a JPG, PNG or WebP picture.")
    kind = "cover" if request.data.get("kind") == "cover" else "logo"
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGBA" if kind == "logo" else "RGB")
    im.thumbnail((600, 600) if kind == "logo" else (1600, 900))
    rel = "companies/%d/%s-%s.webp" % (c.id, kind, secrets.token_hex(8))
    os.makedirs(os.path.join(settings.MEDIA_ROOT, os.path.dirname(rel)), exist_ok=True)
    im.save(os.path.join(settings.MEDIA_ROOT, rel), "WEBP", quality=85)
    setattr(c, kind, rel); c.save(update_fields=[kind, "updated_at"])
    return Response(_out(c, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def domain(request, pk):
    """Step 1: {domain} gets the file to upload; {check: true} checks it. Same safe check as business cards."""
    from bizcards.views import DOMAIN, _fetch_verify, _host
    c = Company.objects.filter(pk=pk, owner=request.user).first()
    if not c:
        return _err("Company not found.", 404)
    if request.data.get("check"):
        if not c.domain or not c.domain_token:
            return _err("Enter your website first.")
        key = "compverify:%d:%s" % (c.id, timezone.localdate()); n = cache.get(key, 0)
        if n >= 15:
            return _err("That's a lot of checks today. Try again tomorrow.")
        cache.set(key, n + 1, 90000)
        text, e = _fetch_verify(c.domain)
        if e:
            return _err(e)
        if ("xpertcreation-verification=" + c.domain_token) not in text:
            return _err("The file is there, but the code inside doesn't match. Upload the file exactly as downloaded.")
        c.domain_verified_at = timezone.now()
        if not c.website: c.website = "https://" + c.domain
        c.save(update_fields=["domain_verified_at", "website", "updated_at"])
        return Response(_out(c, True))
    d = _host(request.data.get("domain") or c.website)
    if not DOMAIN.match(d) or (d.endswith("xpertcreation.com") and not request.user.is_superuser):
        return _err("Enter your company's website, like mycompany.com.")
    if d != c.domain or not c.domain_token:
        c.domain, c.domain_token, c.domain_verified_at = d, secrets.token_hex(16), None
        c.save(update_fields=["domain", "domain_token", "domain_verified_at", "updated_at"])
    return Response(_out(c, True))


MAGIC = [(b"%PDF", "pdf"), (b"\xff\xd8\xff", "jpg"), (b"\x89PNG", "png")]


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def docs(request, pk):
    """Step 2 (KYC): upload proof (PDF/JPG/PNG, 5 MB) - kept outside the website, only the owner and moderators can open it."""
    c = Company.objects.filter(pk=pk, owner=request.user).first()
    if not c:
        return _err("Company not found.", 404)
    if request.method == "DELETE":
        x = c.docs.filter(pk=request.data.get("doc")).first()
        if x and c.status != Company.PENDING:
            _rm(x.path); x.delete()
        return Response(_out(c, True))
    if c.status == Company.PENDING:
        return _err("Your documents are being reviewed. You can add more after the review.")
    f = request.FILES.get("file"); kind = request.data.get("kind")
    if not f or kind not in dict(CompanyDoc.KINDS):
        return _err("Choose the document type and a file.")
    if f.size > 5 * 1024 * 1024:
        return _err("That file is over 5 MB.")
    if c.docs.count() >= 8:
        return _err("You can upload up to 8 documents.")
    head = f.read(8); f.seek(0)
    ext = next((e for m, e in MAGIC if head.startswith(m)), None)
    if not ext:
        return _err("Use a PDF, JPG or PNG file.")
    rel = "c%d/%s.%s" % (c.id, secrets.token_hex(12), ext)
    full = os.path.join(DOCS, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as out:
        for ch in f.chunks():
            out.write(ch)
    os.chmod(full, 0o600)
    CompanyDoc.objects.create(company=c, kind=kind, path=rel, name=_t(f.name, 120), size=f.size)
    return Response(_out(c, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit(request, pk):
    c = Company.objects.filter(pk=pk, owner=request.user).first()
    if not c:
        return _err("Company not found.", 404)
    if not c.domain_verified_at:
        return _err("First verify your website (step 1).")
    if not PHONE.match(c.whatsapp or ""):
        return _err("Add a WhatsApp number - our team will contact you on it to verify.")
    if not c.docs.filter(kind__in=["registration", "cheque"]).exists():
        return _err("Upload the registration certificate or a cheque copy.")
    if c.status == Company.APPROVED:
        return _err("This company is already verified.")
    c.status, c.review_note = Company.PENDING, ""
    c.save(update_fields=["status", "review_note", "updated_at"])
    try:
        from notifications.views import notify_admins
        notify_admins("kyc", "Company KYC to review: %s" % c.name, "/company-review")
    except Exception:
        pass
    return Response(_out(c, True))


def _rm(rel):
    try:
        os.remove(os.path.join(DOCS, rel))
    except OSError:
        pass


def _wipe_docs(c):
    for x in c.docs.all():
        _rm(x.path)
    c.docs.all().delete()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def doc_file(request, doc):
    """Open one KYC document - its company's owner or a moderator only; every opening is logged."""
    x = CompanyDoc.objects.filter(pk=doc).select_related("company").first()
    if not x or not (x.company.owner_id == request.user.id or _reviewer(request.user)):
        raise Http404
    full = os.path.join(DOCS, x.path)
    if not os.path.exists(full):
        raise Http404
    try:
        from auditlog.models import AuditEvent
        AuditEvent.objects.create(user=request.user, action="kyc_doc_view", target="company %d doc %d" % (x.company_id, x.id))
    except Exception:
        pass
    r = FileResponse(open(full, "rb"), as_attachment=False, filename=x.name or os.path.basename(full))
    r["X-Content-Type-Options"] = "nosniff"; r["Cache-Control"] = "private, no-store"
    return r


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def review_list(request):
    if not _reviewer(request.user):
        return _err("Moderators only.", 403)
    rows = Company.objects.filter(status=Company.PENDING).select_related("owner").order_by("updated_at")
    done = Company.objects.filter(status__in=[Company.APPROVED, Company.REJECTED], reviewed_at__isnull=False).order_by("-reviewed_at")[:20]
    def one(c):
        d = _out(c, True)
        d["owner"] = {"name": getattr(c.owner, "full_name", "") or c.owner.email, "email": c.owner.email}
        return d
    return Response({"pending": [one(c) for c in rows], "recent": [one(c) for c in done]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review(request, pk):
    if not _reviewer(request.user):
        return _err("Moderators only.", 403)
    c = Company.objects.filter(pk=pk).first()
    act = request.data.get("action")
    if not c or act not in ("approve", "reject"):
        return _err("Choose approve or reject.")
    note = _t(request.data.get("note"), 500)
    if act == "reject" and not note:
        return _err("Write the reason, so the company knows what to fix.")
    c.status = Company.APPROVED if act == "approve" else Company.REJECTED
    c.review_note, c.reviewed_by, c.reviewed_at = note, request.user, timezone.now()
    c.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
    try:
        from notifications.views import notify
        notify(c.owner, "kyc", ("\u2714 %s is now verified on XpertConnect." % c.name) if act == "approve"
               else ("%s was not verified: %s" % (c.name, note)), "/company/manage")
    except Exception:
        pass
    return Response(_out(c, True))


@api_view(["GET"])
@permission_classes([AllowAny])
def public(request, slug):
    c = Company.objects.filter(slug=slug).select_related("owner").first()
    if not c or not (public_ok(c) or (request.user.is_authenticated and c.owner_id == request.user.id)):
        return _err("This company page is not available.", 404)
    d = _out(c)
    d["mine"] = request.user.is_authenticated and c.owner_id == request.user.id
    d["preview"] = not public_ok(c)
    return Response(d)


@api_view(["GET"])
@permission_classes([AllowAny])
def posts(request, slug):
    c = Company.objects.filter(slug=slug).first()
    if not c or not public_ok(c):
        return Response({"posts": []})
    from feed.models import Post
    try:
        from accounts.views import avatar_url
        av = avatar_url(getattr(c.owner, "avatar", ""))
    except Exception:
        av = ""
    rows = Post.objects.filter(author_id=c.owner_id, visibility="public", hidden=False).order_by("-created_at")[:20]
    return Response({"posts": [{"id": p.id, "body": p.body, "image": _media((p.images or [None])[0]) if p.images else "",
                                "author": c.name, "avatar": _media(c.logo) or av, "when": timezone.localtime(p.created_at).strftime("%d %b %Y"),
                                "reactions": p.reactions_count, "comments": p.comments_count} for p in rows]})


@api_view(["GET"])
@permission_classes([AllowAny])
def search(request):
    q = _t(request.GET.get("q"), 60)
    qs = Company.objects.filter(hidden=False).filter(Q(domain_verified_at__isnull=False) | Q(status=Company.APPROVED))
    if q:
        qs = qs.filter(name__icontains=q)
    return Response({"companies": [{"name": c.name, "slug": c.slug, "city": c.city, "verified": c.status == Company.APPROVED, "logo": _media(c.logo), "pro": bool(getattr(c, "xpro", 0))}
                                   for c in __import__("ads.views", fromlist=["pro_first"]).pro_first(qs)[:8]]})


def place_url(place):
    """A check-in that is exactly a company's name opens that company's page."""
    p = str(place or "").strip()
    if not p:
        return ""
    c = Company.objects.filter(name__iexact=p, hidden=False).filter(Q(domain_verified_at__isnull=False) | Q(status=Company.APPROVED)).first()
    return ("/company/" + c.slug) if c else ""


def page(request, slug):
    try:
        src = open(LAND + "company.html", encoding="utf-8").read()
    except OSError:
        raise Http404
    c = Company.objects.filter(slug=slug).first()
    e = lambda v: html.escape(v, quote=True)
    if not c or not public_ok(c):
        return HttpResponse(src.replace("</head>", '<meta name="robots" content="noindex">\n</head>', 1), status=404 if not c else 200, content_type="text/html; charset=utf-8")
    title = "%s%s \u2014 XpertConnect" % (c.name, (" \u00b7 " + c.city) if c.city else "")
    desc = (c.tagline or c.about or "%s on XpertConnect." % c.name)[:160]
    s = re.sub(r"<title>.*?</title>", "<title>%s</title>" % e(title), src, 1, re.S)
    s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % e(desc), s, 1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s/company/%s">' % (SITE, c.slug), s, 1)
    s = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="%s">' % e(title), s, 1)
    s = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="%s">' % e(desc), s, 1)
    if c.logo:
        s = re.sub(r'<meta property="og:image" content="[^"]*">', '<meta property="og:image" content="%s">' % e(SITE + _media(c.logo)), s, 1)
    r = HttpResponse(s, content_type="text/html; charset=utf-8"); r["Cache-Control"] = "public, max-age=300"
    return r
