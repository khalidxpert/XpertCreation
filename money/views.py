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
