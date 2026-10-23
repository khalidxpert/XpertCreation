"""Video Translate API - /api/vtr/...

new/                 POST {name, size, duration, src, to} or {url, src, to}  start (one video at a time, up to 1 hour)
<id>/chunk/          POST multipart c=<4 MB piece>, i=<number>                 upload in pieces (so big videos survive a bad network)
<id>/done/           POST                                                      all pieces sent - start writing subtitles
<id>/                GET                                                       status, subtitles, translations
<id>/translate/      POST {lang}                                               subtitles in another language
<id>/edit/           POST {lang, i, t}                                         fix one subtitle line
<id>/sub/            GET ?lang=ur&fmt=srt|vtt|txt                              download
<id>/video/          GET                                                       the video (for 2 hours)
<id>/delete/         POST                                                      delete now
mine/                GET                                                       my videos
"""
import ipaddress
import os
import re
import shutil
import socket
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import ai
from .models import Job, Track

MAX_SECONDS = 3600                  # 1 hour
MAX_BYTES = 2 * 1024 ** 3           # 2 GB
CHUNK = 4 * 1024 * 1024             # upload piece
KEEP_HOURS = 2                      # the video and its sound are deleted after this
KEEP_TEXT_DAYS = 30                 # subtitles are kept this long
PER_DAY = 3                         # videos per member per day
SITE_MINUTES_DAY = 180              # audio minutes the whole site may send to the AI per day (free allowance)
MAX_STORE = 8 * 1024 ** 3           # all videos waiting on the server together
MAX_TRACKS = 6                      # languages per video
EXTS = ("mp4", "mov", "m4v", "webm", "mkv", "3gp", "avi", "mpeg", "mpg", "mp3", "m4a", "wav", "ogg", "aac", "opus", "flac", "amr")
BLOCKED = ("youtube.com", "youtu.be", "facebook.com", "fb.watch", "fb.com", "instagram.com", "tiktok.com", "vimeo.com",
           "twitter.com", "x.com", "dailymotion.com", "netflix.com", "snapchat.com", "likee.video")
ACTIVE = ("uploading", "downloading", "queued", "working")


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def vdir():
    return getattr(settings, "VTR_DIR", "/var/lib/xpertcreation/vtr")


def jdir(j):
    return os.path.join(vdir(), str(j.id))


def video_path(j):
    return os.path.join(jdir(j), "video." + j.ext)


def _free_pass(u):
    return bool(u.is_superuser)


def site_minutes_today():
    since = timezone.now() - timedelta(hours=24)
    return Job.objects.filter(created_at__gte=since).aggregate(m=Sum("minutes"))["m"] or 0


def store_used():
    n = 0
    for j in Job.objects.filter(video_gone=False).only("got"):
        n += j.got
    return n


def blocked_host(url):
    h = (urlparse(url).hostname or "").lower()
    return any(h == b or h.endswith("." + b) for b in BLOCKED)


def safe_host(host):
    """No downloads from this server's own network or private addresses."""
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for i in infos:
        ip = ipaddress.ip_address(i[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
    return True


def direct_url(url):
    """Google Drive and Dropbox share links -> their download link."""
    u = url.strip()
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:export=download&)?id=)([\w-]{10,})", u)
    if m:
        return "https://drive.google.com/uc?export=download&id=" + m.group(1)
    if "dropbox.com/" in u:
        u = re.sub(r"([?&])dl=0", r"\1dl=1", u)
        if "dl=1" not in u:
            u += ("&" if "?" in u else "?") + "dl=1"
    return u


def _lang_name(c):
    return ai.LANGS.get(c, (c, c, c))[0] if c else ""


def _shape(j, full=False):
    left = max(0, int((j.expires_at - timezone.now()).total_seconds()))
    d = {"id": j.id, "title": j.title, "status": j.status, "status_label": dict(Job.STATES).get(j.status, j.status), "progress": j.progress,
         "error": j.error, "duration": round(j.duration), "src": j.src_lang, "lang": j.lang, "lang_name": _lang_name(j.lang),
         "rtl": j.lang in ai.RTL, "got": j.got, "size": j.size, "chunks": j.chunks, "chunk_size": CHUNK, "url": bool(j.url),
         "video": (not j.video_gone and j.status != "failed" and os.path.exists(video_path(j))), "video_left": left if not j.video_gone else 0,
         "created": j.created_at.isoformat(), "lines": len(j.segments or [])}
    if full:
        d["segments"] = j.segments or []
        d["tracks"] = [{"lang": t.lang, "name": _lang_name(t.lang), "status": t.status, "progress": t.progress, "rtl": t.lang in ai.RTL,
                        "segments": t.segments if t.status == "ready" else []} for t in j.tracks.all().order_by("id")]
    return d


def _mine(request, pk):
    return Job.objects.filter(pk=pk, user=request.user).first()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    qs = Job.objects.filter(user=request.user).order_by("-id")[:30]
    langs = [{"code": k, "name": v[0], "native": v[1]} for k, v in ai.LANGS.items()]
    since = timezone.now() - timedelta(hours=24)
    used = Job.objects.filter(user=request.user, created_at__gte=since).exclude(status="failed").count()
    return Response({"jobs": [_shape(j) for j in qs], "langs": langs, "limits": {
        "max_minutes": MAX_SECONDS // 60, "per_day": PER_DAY, "used_today": used, "keep_hours": KEEP_HOURS, "keep_days": KEEP_TEXT_DAYS,
        "max_mb": MAX_BYTES // (1024 * 1024), "unlimited": _free_pass(request.user)}, "ai_ready": ai.ready()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def new(request):
    u, v = request.user, request.data
    if not ai.ready():
        return _err("Video Translate is not switched on yet. Please try again later.", 503)
    if not cache.add("vtr:new:%d" % u.pk, 1, 5):
        return _err("One moment, please.", 429)
    busy = Job.objects.filter(user=u, status__in=ACTIVE).first()
    if busy:
        return _err("You already have a video being processed. Wait for it to finish, or delete it, then add the next one.", 409)
    since = timezone.now() - timedelta(hours=24)
    if not _free_pass(u) and Job.objects.filter(user=u, created_at__gte=since).exclude(status="failed").count() >= PER_DAY:
        return _err("You can translate %d videos a day. Please come back tomorrow." % PER_DAY, 429)
    if site_minutes_today() >= SITE_MINUTES_DAY:
        return _err("Video Translate is very busy today. Please try again tomorrow.", 503)
    if store_used() >= MAX_STORE:
        return _err("The server is busy with other videos. Please try again in an hour.", 503)
    src = str(v.get("src") or "auto")[:8]
    src = src if src == "auto" or src in ai.LANGS else "auto"
    to = str(v.get("to") or "")[:8]
    to = to if to in ai.LANGS else ""
    url = str(v.get("url") or "").strip()[:600]
    exp = timezone.now() + timedelta(hours=KEEP_HOURS)
    if url:
        if not re.match(r"^https?://", url, re.I):
            return _err("Paste a full link that starts with https://")
        if blocked_host(url):
            return _err("Videos from YouTube, Facebook, Instagram, TikTok, Vimeo and similar sites cannot be downloaded - their rules do not allow it. "
                        "Upload the video file from your phone, or paste a Google Drive or Dropbox link to your own video.")
        url = direct_url(url)
        h = urlparse(url).hostname or ""
        if not safe_host(h):
            return _err("That link cannot be opened.")
        name = (os.path.basename(urlparse(url).path) or h)[:140]
        j = Job.objects.create(user=u, title=str(v.get("name") or name)[:140], url=url, src_lang=src, want=to, status="downloading", expires_at=exp)
        os.makedirs(jdir(j), exist_ok=True)
        return Response(_shape(j), status=201)
    name = str(v.get("name") or "video")[:140]
    ext = (name.rsplit(".", 1)[-1].lower() if "." in name else "mp4")[:6]
    if ext not in EXTS:
        return _err("Choose a video or audio file (mp4, mov, webm, mkv, 3gp, mp3, m4a, wav...).")
    try:
        size, dur = int(v.get("size") or 0), float(v.get("duration") or 0)
    except (TypeError, ValueError):
        return _err("Choose the video again.")
    if size <= 0:
        return _err("That file is empty.")
    if size > MAX_BYTES:
        return _err("The video is too big (more than %d GB). Send a shorter or smaller video." % (MAX_BYTES // 1024 ** 3))
    if dur > MAX_SECONDS + 5:
        return _err("The video is %d minutes long. Videos can be up to %d minutes." % (round(dur / 60), MAX_SECONDS // 60))
    j = Job.objects.create(user=u, title=name, src_lang=src, want=to, size=size, ext=ext, duration=dur, status="uploading", expires_at=exp)
    os.makedirs(jdir(j), exist_ok=True)
    return Response(_shape(j), status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def chunk(request, pk):
    j = _mine(request, pk)
    if not j or j.status != "uploading":
        return _err("This upload is closed. Start again.", 404)
    try:
        i = int(request.data.get("i"))
    except (TypeError, ValueError):
        return _err("Bad piece.")
    f = request.FILES.get("c")
    if not f:
        return _err("Bad piece.")
    if i < j.chunks:
        return Response({"got": j.got, "chunks": j.chunks})            # already have it (sent twice after a network drop)
    if i != j.chunks:
        return _err("Pieces out of order. Start again.", 409)
    if f.size > CHUNK + 1024 or j.got + f.size > j.size:
        return _err("The file is bigger than expected. Start again.", 400)
    with open(video_path(j), "ab") as out:
        for part in f.chunks():
            out.write(part)
    Job.objects.filter(pk=j.pk).update(got=j.got + f.size, chunks=j.chunks + 1)
    return Response({"got": j.got + f.size, "chunks": j.chunks + 1})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def done(request, pk):
    j = _mine(request, pk)
    if not j or j.status != "uploading":
        return _err("Not found.", 404)
    if j.got != j.size:
        return _err("The upload is not complete yet.")
    j.status = "queued"; j.save(update_fields=["status"])
    return Response(_shape(j))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail(request, pk):
    j = _mine(request, pk)
    if not j:
        return _err("Not found.", 404)
    return Response(_shape(j, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def translate(request, pk):
    j = _mine(request, pk)
    if not j or j.status != "ready":
        return _err("The subtitles are not ready yet.", 404)
    to = str(request.data.get("lang") or "")[:8]
    if to not in ai.LANGS:
        return _err("Pick a language.")
    if to == j.lang:
        return Response(_shape(j, full=True))
    t = Track.objects.filter(job=j, lang=to).first()
    if t and t.status == "failed":
        t.status, t.progress = "queued", 0; t.save(update_fields=["status", "progress"])
    elif not t:
        if Track.objects.filter(job=j).count() >= MAX_TRACKS:
            return _err("Up to %d languages per video." % MAX_TRACKS)
        Track.objects.create(job=j, lang=to)
    return Response(_shape(j, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit(request, pk):
    j = _mine(request, pk)
    if not j or j.status != "ready":
        return _err("Not found.", 404)
    lang = str(request.data.get("lang") or j.lang)
    try:
        i = int(request.data.get("i"))
    except (TypeError, ValueError):
        return _err("Bad line.")
    text = re.sub(r"\s+", " ", str(request.data.get("t") or "")).strip()[:500]
    obj = j if lang == j.lang else Track.objects.filter(job=j, lang=lang, status="ready").first()
    if not obj or not (0 <= i < len(obj.segments)):
        return _err("Bad line.")
    segs = list(obj.segments); segs[i] = dict(segs[i], t=text); obj.segments = segs
    obj.save(update_fields=["segments"])
    return Response({"ok": True})


def _fmt_time(s, sep):
    s = max(0.0, float(s)); h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return "%02d:%02d:%06.3f" % (h, m, sec) if sep == "." else ("%02d:%02d:%06.3f" % (h, m, sec)).replace(".", ",")


def as_vtt(segs):
    return "WEBVTT\n\n" + "\n".join("%s --> %s\n%s\n" % (_fmt_time(x["s"], "."), _fmt_time(x["e"], "."), x["t"]) for x in segs if x.get("t"))


def as_srt(segs):
    out, n = [], 0
    for x in segs:
        if x.get("t"):
            n += 1; out.append("%d\n%s --> %s\n%s\n" % (n, _fmt_time(x["s"], ","), _fmt_time(x["e"], ","), x["t"]))
    return "\n".join(out)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sub(request, pk):
    j = _mine(request, pk)
    if not j or j.status != "ready":
        return _err("Not found.", 404)
    lang = request.GET.get("lang") or j.lang
    segs = j.segments if lang == j.lang else (Track.objects.filter(job=j, lang=lang, status="ready").values_list("segments", flat=True).first() or [])
    fmt = request.GET.get("fmt", "srt")
    if fmt == "vtt":
        body, ct = as_vtt(segs), "text/vtt"
    elif fmt == "txt":
        body, ct = "\n".join(x["t"] for x in segs if x.get("t")), "text/plain"
    else:
        fmt, body, ct = "srt", as_srt(segs), "application/x-subrip"
    base = re.sub(r"[^\w\- ]+", "", (j.title.rsplit(".", 1)[0] or "video"))[:60].strip() or "video"
    r = HttpResponse(("﻿" if fmt != "vtt" else "") + body, content_type=ct + "; charset=utf-8")
    if request.GET.get("dl"):
        r["Content-Disposition"] = 'attachment; filename="%s.%s.%s"' % (base, lang, fmt)
    return r


VIDEO_TYPES = {"mp4": "video/mp4", "m4v": "video/mp4", "mov": "video/quicktime", "webm": "video/webm", "mkv": "video/x-matroska", "3gp": "video/3gpp",
               "avi": "video/x-msvideo", "mpeg": "video/mpeg", "mpg": "video/mpeg", "mp3": "audio/mpeg", "m4a": "audio/mp4", "wav": "audio/wav",
               "ogg": "audio/ogg", "aac": "audio/aac", "opus": "audio/ogg", "flac": "audio/flac", "amr": "audio/amr"}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def video(request, pk):
    j = _mine(request, pk)
    if not j or j.video_gone or j.status in ("uploading", "downloading") or not os.path.exists(video_path(j)):
        return _err("This video was deleted from the server (videos are kept %d hours). Open the file from your phone to watch it with the subtitles." % KEEP_HOURS, 404)
    ct = VIDEO_TYPES.get(j.ext, "application/octet-stream")
    if getattr(settings, "VTR_ACCEL", True):
        r = HttpResponse(content_type=ct)
        r["X-Accel-Redirect"] = "/_xcvtr/%d/video.%s" % (j.id, j.ext)
    else:
        r = FileResponse(open(video_path(j), "rb"), content_type=ct)
    r["Cache-Control"] = "private, max-age=3600"
    r["X-Content-Type-Options"] = "nosniff"
    return r


def remove_files(j):
    shutil.rmtree(jdir(j), ignore_errors=True)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete(request, pk):
    j = _mine(request, pk)
    if not j:
        return _err("Not found.", 404)
    remove_files(j); j.delete()
    return Response({"ok": True})
