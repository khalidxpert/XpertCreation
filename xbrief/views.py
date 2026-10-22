import re
import secrets
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import store
from .models import BUILTIN, BUILTIN_KEYS, Doc, Folder, Share

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 150 * 1024 * 1024
MAX_DOCS = 300
MAX_FOLDERS = 30
SHARE_HOURS = (1, 24, 72, 168)
KINDS = {  # sniffed from the first bytes, not trusted from the browser
    "application/pdf": (b"%PDF",), "image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG",),
    "image/webp": (b"RIFF",), "application/zip": (b"PK\x03\x04",), "application/msword": (b"\xd0\xcf\x11\xe0",),
}
OFFICE = {"docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
          "doc": "application/msword", "xls": "application/vnd.ms-excel"}


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


def _slow(user, what, secs):
    k = "xbrief:%s:%s" % (what, user.pk)
    if cache.get(k):
        return True
    cache.set(k, 1, secs)
    return False


def _sniff(head, fname):
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    for mime, sigs in KINDS.items():
        if any(head.startswith(s) for s in sigs):
            if mime == "image/webp" and head[8:12] != b"WEBP":
                continue
            if mime == "application/zip":
                return OFFICE.get(ext) if ext in ("docx", "xlsx", "pptx") else None
            if mime == "application/msword":
                return OFFICE.get(ext) if ext in ("doc", "xls") else None
            return mime
    return None


def _date(v):
    if v in (None, ""):
        return None, None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
        return None, "Pick a proper expiry date."
    try:
        d = date.fromisoformat(str(v))
    except ValueError:
        return None, "Pick a proper expiry date."
    if d.year < 1990 or d.year > 2100:
        return None, "Pick a proper expiry date."
    return d, None


def _folder_ok(user, key):
    if key in BUILTIN_KEYS:
        return True
    m = re.fullmatch(r"f(\d+)", key or "")
    return bool(m) and Folder.objects.filter(owner=user, pk=int(m.group(1))).exists()


def _clean(s, n):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(s or "")).strip()[:n]


def shape(d):
    days = (d.expires - timezone.localdate()).days if d.expires else None
    return {"id": d.id, "folder": d.folder, "title": d.title, "note": d.note, "fname": d.fname, "mime": d.mime,
            "size": d.size, "expires": d.expires.isoformat() if d.expires else None, "days_left": days,
            "created": d.created_at.isoformat(), "url": "/api/brief/docs/%d/file/" % d.id}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home(request):
    u = request.user
    docs = list(Doc.objects.filter(owner=u))
    count = {}
    for d in docs:
        count[d.folder] = count.get(d.folder, 0) + 1
    folders = [{"key": k, "name": n, "icon": i, "ur": ur, "builtin": True, "count": count.get(k, 0)} for k, n, i, ur in BUILTIN]
    folders += [{"key": "f%d" % f.id, "id": f.id, "name": f.name, "icon": f.icon, "ur": "", "builtin": False, "count": count.get("f%d" % f.id, 0)}
                for f in Folder.objects.filter(owner=u)]
    used = sum(d.size for d in docs)
    return Response({"folders": folders, "docs": [shape(d) for d in docs], "used": used, "limit": MAX_TOTAL, "max_file": MAX_FILE})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def folders(request):
    u = request.user
    name = _clean(request.data.get("name"), 40)
    icon = _clean(request.data.get("icon"), 8) or "\U0001F4C2"
    if len(name) < 2:
        return _err("Give the folder a name.")
    if Folder.objects.filter(owner=u).count() >= MAX_FOLDERS:
        return _err("You have %d folders, the most allowed." % MAX_FOLDERS)
    if Folder.objects.filter(owner=u, name__iexact=name).exists() or name.lower() in [b[1].lower() for b in BUILTIN]:
        return _err("You already have a folder with that name.")
    f = Folder.objects.create(owner=u, name=name, icon=icon)
    return Response({"key": "f%d" % f.id, "id": f.id, "name": f.name, "icon": f.icon, "builtin": False, "count": 0}, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def folder(request, pk):
    f = Folder.objects.filter(owner=request.user, pk=pk).first()
    if not f:
        return _err("Folder not found.", 404)
    if request.method == "DELETE":
        Doc.objects.filter(owner=request.user, folder="f%d" % f.id).update(folder="other")
        f.delete()
        return Response({"ok": True})
    name = _clean(request.data.get("name"), 40)
    if len(name) < 2:
        return _err("Give the folder a name.")
    f.name = name
    if request.data.get("icon"):
        f.icon = _clean(request.data.get("icon"), 8)
    f.save()
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload(request):
    u = request.user
    up = request.FILES.get("file")
    if not up:
        return _err("Choose a file.")
    if up.size > MAX_FILE:
        return _err("That file is over 8 MB. Scan it again with fewer pages, or make it smaller.", 413)
    if Doc.objects.filter(owner=u).count() >= MAX_DOCS:
        return _err("Your briefcase is full (%d documents). Delete some old ones first." % MAX_DOCS)
    used = Doc.objects.filter(owner=u).aggregate(s=Sum("size"))["s"] or 0
    if used + up.size > MAX_TOTAL:
        return _err("Your briefcase is full (150 MB). Delete some old documents first.")
    if _slow(u, "up", 1):
        return _err("One moment, still saving the last one.", 429)
    data = up.read()
    fname = _clean(up.name.replace("/", "_").replace("\\", "_"), 120) or "document"
    mime = _sniff(data[:16], fname)
    if not mime:
        return _err("Only PDF, pictures (JPG, PNG, WEBP) and Word, Excel or PowerPoint files can be saved.")
    folder_key = request.data.get("folder") or "other"
    if not _folder_ok(u, folder_key):
        folder_key = "other"
    exp, bad = _date(request.data.get("expires"))
    if bad:
        return _err(bad)
    title = _clean(request.data.get("title"), 120) or fname.rsplit(".", 1)[0][:120]
    name = store.save(data)
    d = Doc.objects.create(owner=u, folder=folder_key, title=title, note=_clean(request.data.get("note"), 300),
                           fname=fname, mime=mime, size=len(data), path=name, expires=exp)
    return Response(shape(d), status=201)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def doc(request, pk):
    d = Doc.objects.filter(owner=request.user, pk=pk).first()
    if not d:
        return _err("Document not found.", 404)
    if request.method == "GET":
        return Response(shape(d))
    if request.method == "DELETE":
        d.delete()
        return Response({"ok": True})
    v = request.data
    if "title" in v:
        t = _clean(v.get("title"), 120)
        if not t:
            return _err("Give it a name.")
        d.title = t
    if "note" in v:
        d.note = _clean(v.get("note"), 300)
    if "folder" in v:
        if not _folder_ok(request.user, v.get("folder")):
            return _err("Folder not found.")
        d.folder = v.get("folder")
    if "expires" in v:
        exp, bad = _date(v.get("expires"))
        if bad:
            return _err(bad)
        if exp != d.expires:
            d.reminded = ""
        d.expires = exp
    d.save()
    return Response(shape(d))


def _file(d, download=False):
    try:
        data = store.load(d.path)
    except Exception:
        return HttpResponse("This file could not be opened.", status=410, content_type="text/plain")
    r = HttpResponse(data, content_type=d.mime)
    inline = d.mime.startswith("image/") or d.mime == "application/pdf"
    fn = re.sub(r'[^\w.\- ]', "_", d.fname)[:100] or "document"
    r["Content-Disposition"] = '%s; filename="%s"' % ("inline" if inline and not download else "attachment", fn)
    r["Cache-Control"] = "private, no-store"
    r["X-Content-Type-Options"] = "nosniff"
    r["Content-Security-Policy"] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"
    r["Referrer-Policy"] = "no-referrer"
    return r


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def doc_file(request, pk):
    d = Doc.objects.filter(owner=request.user, pk=pk).first()
    if not d:
        return _err("Document not found.", 404)
    return _file(d, request.GET.get("dl") == "1")


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def share(request, pk):
    d = Doc.objects.filter(owner=request.user, pk=pk).first()
    if not d:
        return _err("Document not found.", 404)
    now = timezone.now()
    if request.method == "DELETE":
        n = d.shares.all().delete()[0]
        return Response({"ok": True, "stopped": n})
    if request.method == "GET":
        return Response({"links": [{"expires_at": s.expires_at.isoformat(), "views": s.views}
                                   for s in d.shares.filter(expires_at__gt=now)]})
    try:
        hours = int(request.data.get("hours", 24))
    except (TypeError, ValueError):
        hours = 24
    if hours not in SHARE_HOURS:
        hours = 24
    if _slow(request.user, "sh", 2):
        return _err("One moment.", 429)
    Share.objects.filter(doc__owner=request.user, expires_at__lt=now).delete()
    s = Share.objects.create(doc=d, token=secrets.token_urlsafe(24), expires_at=now + timedelta(hours=hours))
    return Response({"url": "/api/brief/s/%s/" % s.token, "expires_at": s.expires_at.isoformat(), "hours": hours}, status=201)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def shared(request, token):
    s = Share.objects.select_related("doc").filter(token=token, expires_at__gt=timezone.now()).first() if re.fullmatch(r"[\w-]{20,48}", token) else None
    if not s:
        return HttpResponse("<!doctype html><meta name=viewport content='width=device-width'><body style='font-family:system-ui;padding:40px;text-align:center'>"
                            "<h2>This link has ended</h2><p>Ask the owner to share the document again.</p>"
                            "<p dir=rtl>یہ لنک ختم ہو چکا ہے۔ مالک سے دوبارہ شیئر کرنے کو کہیں۔</p><p><a href='https://xpertcreation.com/briefcase'>XpertCreation · My Briefcase</a></p>",
                            status=404, content_type="text/html")
    Share.objects.filter(pk=s.pk).update(views=s.views + 1)
    r = _file(s.doc, request.GET.get("dl") == "1")
    r["X-Robots-Tag"] = "noindex, nofollow"
    return r
