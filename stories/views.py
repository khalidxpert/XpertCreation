"""Status (stories): 24-hour photos or text on a colour, for connections or everyone."""
import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Story, StoryView

BGS = {"blue", "sunset", "green", "night", "pink", "gold", "sky", "red", "purple", "black"}
PER_DAY = 15


def _err(m, code=400):
    return Response({"detail": m}, status=code)


def _person(u):
    try:
        from accounts.views import avatar_url
        av = avatar_url(u.avatar)
    except Exception:
        av = ""
    return {"id": u.pk, "name": (getattr(u, "full_name", "") or getattr(u, "username", "") or "Member").strip(), "username": getattr(u, "username", "") or "", "avatar_url": av}


def _media(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p else ""


def _ago(dt):
    s = int((timezone.now() - dt).total_seconds())
    return "now" if s < 60 else ("%dm" % (s // 60) if s < 3600 else "%dh" % (s // 3600))


def _visible(u):
    try:
        from feed.views import _connected_ids
        conn = set(_connected_ids(u))
    except Exception:
        conn = set()
    now = timezone.now()
    return Story.objects.filter(expires_at__gt=now).filter(Q(user=u) | Q(audience="everyone") | Q(user_id__in=conn)).select_related("user")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def stories(request):
    u = request.user
    if request.method == "GET":
        rows = list(_visible(u).order_by("created_at")[:400])
        seen = set(StoryView.objects.filter(viewer=u, story__in=rows).values_list("story_id", flat=True))
        groups = {}
        for s in rows:
            g = groups.setdefault(s.user_id, {"user": _person(s.user), "mine": s.user_id == u.pk, "items": [], "latest": s.created_at})
            g["items"].append({"id": s.id, "kind": s.kind, "image": _media(s.image), "text": s.text, "bg": s.bg, "when": _ago(s.created_at), "seen": s.id in seen})
            g["latest"] = max(g["latest"], s.created_at)
        out = sorted(groups.values(), key=lambda g: (not g["mine"], all(i["seen"] for i in g["items"]), -g["latest"].timestamp()))
        for g in out:
            g["seen_all"] = all(i["seen"] for i in g["items"]); g.pop("latest")
        return Response({"groups": out[:60]})
    if Story.objects.filter(user=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= PER_DAY:
        return _err("You can share %d stories a day." % PER_DAY)
    aud = "everyone" if request.data.get("audience") == "everyone" else "connections"
    f = request.FILES.get("image")
    s = Story(user=u, audience=aud, expires_at=timezone.now() + timedelta(hours=24))
    if f:
        if f.size > 8 * 1024 * 1024:
            return _err("That picture is over 8 MB.")
        from PIL import Image, ImageOps
        try:
            im = Image.open(f); fmt = im.format; im.load()
        except Exception:
            return _err("That file is not a picture we can read.")
        if fmt not in ("JPEG", "PNG", "WEBP", "GIF"):
            return _err("Use a JPG, PNG or WebP picture.")
        im = ImageOps.exif_transpose(im).convert("RGB"); im.thumbnail((1080, 1920))
        rel = "stories/%d/%s.webp" % (u.pk, secrets.token_hex(10))
        os.makedirs(os.path.join(settings.MEDIA_ROOT, os.path.dirname(rel)), exist_ok=True)
        im.save(os.path.join(settings.MEDIA_ROOT, rel), "WEBP", quality=80)
        s.kind, s.image, s.text = "photo", rel, str(request.data.get("text") or "").strip()[:300]
    else:
        t = str(request.data.get("text") or "").strip()[:300]
        if not t:
            return _err("Add a photo or write something.")
        bg = str(request.data.get("bg") or "blue")
        s.kind, s.text, s.bg = "text", t, bg if bg in BGS else "blue"
    s.save()
    return Response({"id": s.id}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def seen(request, pk):
    s = _visible(request.user).filter(pk=pk).first()
    if s and s.user_id != request.user.pk:
        StoryView.objects.get_or_create(story=s, viewer=request.user)
    return Response({"ok": True})


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def one(request, pk):
    s = Story.objects.filter(pk=pk, user=request.user).first()
    if not s:
        return _err("Story not found.", 404)
    if request.method == "DELETE":
        _remove(s); return Response({"deleted": True})
    v = StoryView.objects.filter(story=s).select_related("viewer").order_by("-seen_at")[:300]
    return Response({"viewers": [dict(_person(x.viewer), when=_ago(x.seen_at)) for x in v]})


def _remove(s):
    if s.image:
        try:
            os.remove(os.path.join(settings.MEDIA_ROOT, s.image))
        except OSError:
            pass
    s.delete()
