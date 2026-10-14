"""Money page sync: the member's whole book as one JSON document, encrypted at rest with MONEY_KEY from .env.
GET returns {data, rev, user}; PUT {rev, data} saves only if rev matches (else 409 with the newer copy to merge)."""
import json
import os
import re
from datetime import timedelta

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MoneyBook, MoneySnapshot

MAX_BYTES = 3 * 1024 * 1024
_F = None


def _f():
    global _F
    if _F is None:
        env = open(os.path.join(settings.BASE_DIR, ".env")).read()
        m = re.search(r"^MONEY_KEY=(.*)$", env, re.M)
        _F = Fernet(m.group(1).strip().strip('"\'').encode())
    return _F


def _dec(blob):
    if not blob:
        return None
    return json.loads(_f().decrypt(blob.encode()).decode())


def _enc(data):
    return _f().encrypt(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()).decode()


def _valid(d):
    if not isinstance(d, dict) or not isinstance(d.get("accounts"), list) or not isinstance(d.get("tx"), list):
        return "Not a Money book."
    if len(d["accounts"]) > 300 or len(d["tx"]) > 100000:
        return "Too many accounts or entries."
    for o in d["accounts"] + d["tx"]:
        if not isinstance(o, dict) or not isinstance(o.get("id"), str) or len(o["id"]) > 40:
            return "Bad item in the book."
    if not isinstance(d.get("del", {}), dict):
        return "Bad delete list."
    return ""


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def book(request):
    u = request.user
    if request.method == "GET":
        b = MoneyBook.objects.filter(user=u).first()
        return Response({"data": _dec(b.blob) if b else None, "rev": b.rev if b else 0, "user": u.pk,
                         "updated": b.updated_at.isoformat() if b else ""})
    data, base = request.data.get("data"), request.data.get("rev")
    err = _valid(data)
    if err:
        return Response({"detail": err}, status=400)
    blob = _enc(data)
    if len(blob) > MAX_BYTES:
        return Response({"detail": "Your Money book is too large to save."}, status=413)
    with transaction.atomic():
        b, _ = MoneyBook.objects.select_for_update().get_or_create(user=u)
        if str(base) != str(b.rev):
            return Response({"detail": "changed elsewhere", "data": _dec(b.blob), "rev": b.rev, "user": u.pk}, status=409)
        b.blob, b.rev = blob, b.rev + 1
        b.save()
        last = MoneySnapshot.objects.filter(user=u).order_by("-created_at").first()
        if not last or last.created_at < timezone.now() - timedelta(hours=24):
            MoneySnapshot.objects.create(user=u, blob=blob, rev=b.rev)
            old = list(MoneySnapshot.objects.filter(user=u).order_by("-created_at").values_list("pk", flat=True)[30:])
            if old:
                MoneySnapshot.objects.filter(pk__in=old).delete()
    return Response({"rev": b.rev, "updated": b.updated_at.isoformat()})


# ---- Receipts and payment proofs on entries (setup_money_files_v1). Encrypted with the same MONEY_KEY.
import secrets as _sec5
from django.http import HttpResponse as _Http5
from rest_framework.decorators import parser_classes as _parsers5
from rest_framework.parsers import FormParser as _Form5, MultiPartParser as _Multi5
from .models import MoneyFile

FILE_MB = 8
FILES_PER_USER = 600
_KINDS5 = [(b"%PDF", "application/pdf", "pdf"), (b"\xff\xd8\xff", "image/jpeg", "jpg"), (b"\x89PNG", "image/png", "png"),
           (b"GIF8", "image/gif", "gif"), (b"RIFF", "image/webp", "webp")]


def _files_dir():
    return os.environ.get("XC_MONEY_FILES", "/var/lib/gunicorn-academy/money_files")


def _fpath(f):
    return os.path.join(_files_dir(), str(f.user_id), f.fid + ".bin")


def _fout(f):
    return {"id": f.fid, "name": f.name, "type": f.ctype, "size": f.size, "when": f.created_at.isoformat()}


def _clean_orphans(u):
    """Files older than 2 days that no entry in the member's book points to (entry deleted, or form cancelled)."""
    b = MoneyBook.objects.filter(user=u).first()
    try:
        data = _dec(b.blob) if b else None
    except Exception:
        return
    if not data:
        return
    used = set()
    for t in data.get("tx", []):
        for x in (t.get("files") or []) if isinstance(t, dict) else []:
            if isinstance(x, dict):
                used.add(str(x.get("id")))
    for f in MoneyFile.objects.filter(user=u, created_at__lt=timezone.now() - timedelta(days=2)).exclude(fid__in=used)[:200]:
        try:
            os.remove(_fpath(f))
        except OSError:
            pass
        f.delete()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@_parsers5([_Multi5, _Form5])
def file_add(request):
    u, f = request.user, request.FILES.get("file")
    if not f:
        return Response({"detail": "Choose a picture or PDF."}, status=400)
    if f.size > FILE_MB * 1024 * 1024:
        return Response({"detail": "The file is over %d MB." % FILE_MB}, status=400)
    _clean_orphans(u)
    if MoneyFile.objects.filter(user=u).count() >= FILES_PER_USER:
        return Response({"detail": "You have %d files. Remove some old ones first." % FILES_PER_USER}, status=400)
    raw = f.read()
    kind = next((k for k in _KINDS5 if raw.startswith(k[0]) and (k[2] != "webp" or raw[8:12] == b"WEBP")), None)
    if not kind:
        return Response({"detail": "Only pictures (JPG, PNG, WebP) or PDF."}, status=400)
    name = re.sub(r"[^\w.\- ()]+", "_", os.path.basename(f.name or "receipt"))[:100] or "receipt"
    if not name.lower().endswith("." + kind[2]) and not (kind[2] == "jpg" and name.lower().endswith(".jpeg")):
        name = os.path.splitext(name)[0][:90] + "." + kind[2]
    mf = MoneyFile(user=u, fid=_sec5.token_urlsafe(12)[:16], name=name, ctype=kind[1], size=len(raw))
    os.makedirs(os.path.dirname(_fpath(mf)), mode=0o700, exist_ok=True)
    with open(_fpath(mf), "wb") as fh:
        fh.write(_f().encrypt(raw))
    mf.save()
    return Response(_fout(mf), status=201)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def file_one(request, fid):
    f = MoneyFile.objects.filter(user=request.user, fid=str(fid)[:24]).first()
    if not f:
        return Response({"detail": "File not found."}, status=404)
    if request.method == "DELETE":
        try:
            os.remove(_fpath(f))
        except OSError:
            pass
        f.delete()
        return Response({"ok": True})
    try:
        raw = _f().decrypt(open(_fpath(f), "rb").read())
    except Exception:
        return Response({"detail": "File not found."}, status=404)
    r = _Http5(raw, content_type=f.ctype)
    r["Content-Disposition"] = '%s; filename="%s"' % ("attachment" if request.GET.get("dl") else "inline", f.name.replace('"', ""))
    r["Cache-Control"] = "private, no-store"
    r["X-Content-Type-Options"] = "nosniff"
    return r
