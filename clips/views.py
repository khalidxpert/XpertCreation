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
    try:
        from accounts.views import avatar_url
        return avatar_url(getattr(u, "avatar", "")) or ""
    except Exception:
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


# ---- setup_clipshare_v1: a shared clip link shows that clip (its picture, caption and playable video)
#      on Facebook, WhatsApp and XpertConnect. nginx sends /clips?id=N here; everything else is the normal page.
import html as _h5
import re as _re5
from django.http import HttpResponse as _HR5

_CLIPS_PAGE = "/var/www/xpertcreation-landing/clips.html"
_SITE5 = "https://xpertcreation.com"


def _abs5(u):
    u = str(u or "")
    return u if u.startswith("http") else (_SITE5 + u if u.startswith("/") else "")


def og(request, pk):
    try:
        page = open(_CLIPS_PAGE, encoding="utf-8").read()
    except Exception:
        return _HR5("Not found", status=404)
    c = Clip.objects.filter(pk=pk, status="published", hidden=False).select_related("user").first()
    if c:
        who = _name(c.user)
        cap = _re5.sub(r"\s+", " ", c.caption or "").strip()
        title = (cap[:90] if cap else "A clip by %s" % who) + " — XpertClips"
        desc = "Watch %s's clip on XpertClips · %d likes · %d views. Short videos on XpertCreation." % (who, c.likes, c.views)
        url = "%s/clips?id=%d" % (_SITE5, c.id)
        img = _abs5(c.thumb_url) or _SITE5 + "/brand/og/p/clips.jpg"
        vid = _abs5(c.video_url)

        def setm(page, attr, key, val):
            pat = _re5.compile(r'(<meta %s="%s" content=")[^"]*(")' % (attr, _re5.escape(key)))
            return pat.sub(lambda m: m.group(1) + _h5.escape(val, quote=True) + m.group(2), page, count=1)
        for attr, key, val in (("property", "og:title", title), ("name", "twitter:title", title), ("property", "og:description", desc),
                               ("name", "twitter:description", desc), ("name", "description", desc), ("property", "og:url", url),
                               ("property", "og:image", img), ("name", "twitter:image", img), ("property", "og:type", "video.other" if vid else "website")):
            page = setm(page, attr, key, val)
        page = _re5.sub(r"<title>[^<]*</title>", "<title>%s</title>" % _h5.escape(title), page, count=1)
        page = _re5.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + url + m.group(2), page, count=1)
        page = _re5.sub(r'<meta property="og:image:(?:width|height)" content="[^"]*">\n?', "", page)
        if vid:
            vt = "application/x-mpegURL" if ".m3u8" in vid else "video/mp4"
            tags = ('<meta property="og:video" content="%s">\n<meta property="og:video:secure_url" content="%s">\n'
                    '<meta property="og:video:type" content="%s">\n<meta property="og:video:width" content="720">\n'
                    '<meta property="og:video:height" content="1280">\n') % (_h5.escape(vid, quote=True), _h5.escape(vid, quote=True), vt)
            page = page.replace('<meta property="og:locale"', tags + '<meta property="og:locale"', 1)
    r = _HR5(page)
    r["Cache-Control"] = "public, max-age=300"
    return r
