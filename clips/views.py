"""XpertClips: TikTok-style short videos. Upload -> processed in the background (ffmpeg) -> stored on Cloudflare via the upload worker."""
import importlib
import math
import os
import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Clip, ClipComment, ClipLike, ClipReport

INCOMING = "/var/lib/xc-clips/incoming"
MAX_MB, PER_DAY, TRUST_AFTER, HIDE_AT = 100, 5, 3, 3
OK_TYPES = ("video/mp4", "video/quicktime", "video/webm", "video/3gpp", "video/x-matroska", "video/x-m4v")


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _name(u):
    return ((getattr(u, "full_name", "") or "").strip() or getattr(u, "username", "") or "Member") if u else "Member"


def _avatar(u):
    for f in ("avatar_url", "photo_url", "avatar", "photo"):
        v = getattr(u, f, None)
        if v:
            return v if isinstance(v, str) else getattr(v, "url", "")
    return ""


def notify(user, text, link):
    for mod in ("notifications.utils", "notifications.views", "notifications.models", "notifications"):
        try:
            f = getattr(importlib.import_module(mod), "notify", None)
            if callable(f):
                f(user, "clip", text, link); return
        except Exception:
            continue


def _check(text):
    try:
        from afsanay.moderation import check
        return check(text) if text.strip() else (True, "", "")
    except Exception:
        return True, "", "unchecked"


def trusted(u):
    return _staff(u) or Clip.objects.filter(user=u, status="published").count() >= TRUST_AFTER


def _out(c, liked=False):
    return {"id": c.id, "video": c.video_url, "thumb": c.thumb_url, "caption": c.caption, "user": _name(c.user), "user_id": c.user_id,
            "avatar": _avatar(c.user), "username": getattr(c.user, "username", ""), "likes": c.likes, "comments": c.comments, "views": c.views,
            "liked": liked, "status": c.status, "note": c.note, "created": c.created_at.isoformat()}


@api_view(["GET"])
@permission_classes([AllowAny])
def feed(request):
    u = request.user; g = request.GET
    base = Clip.objects.filter(status="published", hidden=False).select_related("user")
    if g.get("user", "").isdigit():
        qs = list(base.filter(user_id=int(g["user"])).order_by("-created_at")[:60])
    elif g.get("id", "").isdigit():
        qs = list(base.filter(id=int(g["id"])))
    else:
        seen = {int(x) for x in g.get("seen", "").split(",")[:200] if x.isdigit()}
        now = timezone.now(); pool = [c for c in base.order_by("-created_at")[:600] if c.id not in seen]
        def score(c):
            age = max(0.0, (now - c.created_at).total_seconds() / 3600)
            return (c.likes * 2 + c.comments * 3 + c.views * 0.05 + 1) / math.pow(age + 2, 1.15) * random.uniform(0.75, 1.25)
        qs = sorted(pool, key=score, reverse=True)[:8]
        if not qs and seen:
            qs = sorted(base.order_by("-created_at")[:200], key=lambda c: random.random())[:8]
    mine = set(ClipLike.objects.filter(user=u, clip_id__in=[c.id for c in qs]).values_list("clip_id", flat=True)) if u.is_authenticated else set()
    return Response({"clips": [_out(c, c.id in mine) for c in qs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload(request):
    u = request.user; f = request.FILES.get("video")
    if not f:
        return Response({"detail": "Choose a video."}, status=400)
    if f.size > MAX_MB * 1024 * 1024:
        return Response({"detail": "That video is too big (up to %d MB)." % MAX_MB}, status=400)
    if (f.content_type or "") not in OK_TYPES and not f.name.lower().endswith((".mp4", ".mov", ".webm", ".3gp", ".mkv", ".m4v")):
        return Response({"detail": "Please choose a video file."}, status=400)
    if Clip.objects.filter(user=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= PER_DAY:
        return Response({"detail": "You can post up to %d clips a day." % PER_DAY}, status=429)
    caption = str(request.data.get("caption") or "").strip()[:300]
    ok, why, kind = _check(caption)
    if not ok and kind == "rules":
        return Response({"detail": why}, status=400)
    os.makedirs(INCOMING, exist_ok=True)
    path = os.path.join(INCOMING, "%s%s" % (uuid.uuid4().hex, os.path.splitext(f.name)[1].lower()[:6] or ".mp4"))
    with open(path, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)
    c = Clip.objects.create(user=u, caption=caption, src_path=path, note=why if not ok else "")
    return Response({"id": c.id, "status": "processing", "detail": "Uploaded. We are preparing your clip; it usually takes about a minute."}, status=201)


@api_view(["GET", "DELETE"])
@permission_classes([AllowAny])
def clip(request, pk):
    u = request.user; c = Clip.objects.filter(pk=pk).select_related("user").first()
    if not c:
        return Response({"detail": "Not found."}, status=404)
    own = u.is_authenticated and (c.user_id == u.pk or _staff(u))
    if request.method == "DELETE":
        if not own:
            return Response({"detail": "Only the creator can delete this."}, status=403)
        c.delete(); return Response({"deleted": True})
    if (c.status != "published" or c.hidden) and not own:
        return Response({"detail": "Not found."}, status=404)
    return Response(_out(c, u.is_authenticated and ClipLike.objects.filter(user=u, clip=c).exists()))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    return Response({"clips": [_out(c) for c in Clip.objects.filter(user=request.user).order_by("-created_at")[:60]]})


@api_view(["POST", "GET"])
@permission_classes([AllowAny])
def act(request, pk, what):
    u = request.user; c = Clip.objects.filter(pk=pk, status="published", hidden=False).first()
    if not c:
        return Response({"detail": "Not found."}, status=404)
    if what == "view":
        Clip.objects.filter(pk=pk).update(views=F("views") + 1); return Response({"ok": True})
    if what == "comments" and request.method == "GET":
        return Response({"comments": [{"id": x.id, "who": _name(x.user), "body": x.body, "date": x.created_at.isoformat()} for x in c.clip_comments.select_related("user").order_by("-id")[:100]]})
    if not u.is_authenticated:
        return Response({"detail": "Sign in first."}, status=401)
    if what == "like":
        o = ClipLike.objects.filter(user=u, clip=c).first()
        if o:
            o.delete(); Clip.objects.filter(pk=pk).update(likes=F("likes") - 1); return Response({"liked": False})
        ClipLike.objects.create(user=u, clip=c); Clip.objects.filter(pk=pk).update(likes=F("likes") + 1); return Response({"liked": True})
    if what == "comments":
        body = str(request.data.get("body") or "").strip()[:500]
        if len(body) < 1:
            return Response({"detail": "Write a comment."}, status=400)
        ok, why, kind = _check(body)
        if not ok:
            return Response({"detail": why if kind == "rules" else "This comment can't be posted. Please keep it kind."}, status=400)
        if ClipComment.objects.filter(user=u, created_at__gte=timezone.now() - timedelta(minutes=5)).count() >= 15:
            return Response({"detail": "Slow down a little."}, status=429)
        ClipComment.objects.create(clip=c, user=u, body=body); Clip.objects.filter(pk=pk).update(comments=F("comments") + 1)
        if c.user_id != u.pk:
            notify(c.user, "%s commented on your clip" % _name(u), "/clips?id=%d" % c.id)
        return Response({"ok": True}, status=201)
    if what == "report":
        ClipReport.objects.get_or_create(clip=c, user=u, defaults={"reason": str(request.data.get("reason") or "")[:300]})
        if ClipReport.objects.filter(clip=c).count() >= HIDE_AT:
            c.hidden = True; c.save(update_fields=["hidden"])
        return Response({"reported": True})
    return Response({"detail": "Unknown action."}, status=400)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def review(request):
    if not _staff(request.user):
        return Response({"detail": "Staff only."}, status=403)
    if request.method == "GET":
        P = Clip.objects.filter(status="pending").select_related("user").order_by("created_at")[:50]
        H = Clip.objects.filter(status="published", hidden=True).select_related("user").order_by("-created_at")[:50]
        return Response({"pending": [_out(c) for c in P], "reported": [_out(c) for c in H]})
    c = Clip.objects.filter(pk=request.data.get("id")).first()
    if not c:
        return Response({"detail": "Not found."}, status=404)
    if request.data.get("action") == "approve":
        c.status, c.hidden, c.note = "published", False, ""; c.save()
        ClipReport.objects.filter(clip=c).delete()
        notify(c.user, "Your clip is now live. \U0001F3AC", "/clips?id=%d" % c.id)
    else:
        c.status, c.note = "rejected", str(request.data.get("reason") or "It does not follow our community rules.")[:300]; c.save()
        notify(c.user, "Your clip was not published: %s" % c.note, "/clips?mine=1")
    return Response({"ok": True})
