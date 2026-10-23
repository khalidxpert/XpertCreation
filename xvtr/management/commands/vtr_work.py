"""Every minute (cron): download linked videos, take the sound out with ffmpeg, write subtitles with Whisper,
translate them, and delete videos older than 2 hours. Only one copy runs at a time (lock file)."""
import fcntl
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import timedelta
from urllib.parse import urljoin, urlparse

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from xvtr import ai
from xvtr import views as V
from xvtr.models import Job, Track
from xvtr.shahmukhi import to_shahmukhi

PIECE = 120                 # seconds of sound per AI request
BATCH = 40                  # subtitle lines per translation request
RUN_FOR = 50 * 60           # stop after this, the next minute's run carries on
CT_EXT = {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm", "video/x-matroska": "mkv", "video/3gpp": "3gp",
          "video/x-msvideo": "avi", "video/mpeg": "mpeg", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/wav": "wav",
          "audio/x-wav": "wav", "audio/ogg": "ogg", "audio/aac": "aac", "audio/flac": "flac", "audio/amr": "amr", "application/ogg": "ogg"}


def log(*a):
    print(timezone.now().strftime("%H:%M:%S"), *a, flush=True)


def notify(u, text, link):
    try:
        from notifications.views import notify as n
        n(u, "vtr", text, link)
    except Exception:
        pass


def probe(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                           capture_output=True, text=True, timeout=120)
        return float((r.stdout or "0").strip().splitlines()[0])
    except Exception:
        return 0.0


def fail(j, msg):
    j.status, j.error = "failed", msg[:300]
    j.save(update_fields=["status", "error"])
    shutil.rmtree(os.path.join(V.jdir(j), "a"), ignore_errors=True)
    log("job", j.id, "failed:", msg)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def download(j):
    """A direct link to a video file (Google Drive, Dropbox, any https link to an mp4...). Every hop is checked."""
    url, opener = j.url, urllib.request.build_opener(NoRedirect)
    for _ in range(6):
        p = urlparse(url)
        if p.scheme not in ("http", "https") or V.blocked_host(url) or not V.safe_host(p.hostname or ""):
            return fail(j, "That link cannot be downloaded. Upload the video file instead.")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (XpertCreation Video Translate)"})
        try:
            r = opener.open(req, timeout=30)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urljoin(url, e.headers["Location"]); continue
            return fail(j, "The link answered with error %s. Check that the video is shared with anyone who has the link." % e.code)
        except Exception:
            return fail(j, "The link could not be opened. Check it and try again.")
        break
    else:
        return fail(j, "The link redirects too many times.")
    ct = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if ct.startswith("text/"):
        return fail(j, "That link opens a web page, not a video file. For Google Drive, share the file as 'Anyone with the link' "
                       "(very big Drive files cannot be downloaded this way - upload the file instead).")
    size = int(r.headers.get("Content-Length") or 0)
    if size > V.MAX_BYTES:
        return fail(j, "The video is too big (more than %d GB)." % (V.MAX_BYTES // 1024 ** 3))
    ext = CT_EXT.get(ct) or (os.path.splitext(urlparse(url).path)[1][1:].lower() or "mp4")
    j.ext = ext if ext in V.EXTS else "mp4"
    os.makedirs(V.jdir(j), exist_ok=True)
    got, start = 0, time.time()
    try:
        with open(V.video_path(j), "wb") as out:
            while True:
                b = r.read(1024 * 1024)
                if not b:
                    break
                got += len(b)
                if got > V.MAX_BYTES:
                    raise ValueError("too big")
                if time.time() - start > 25 * 60:
                    raise TimeoutError()
                out.write(b)
                if got % (32 * 1024 * 1024) < len(b):
                    Job.objects.filter(pk=j.pk).update(got=got)
    except ValueError:
        return fail(j, "The video is too big (more than %d GB)." % (V.MAX_BYTES // 1024 ** 3))
    except Exception:
        return fail(j, "The download stopped. Try again, or upload the file instead.")
    j.got = j.size = got
    j.duration = probe(V.video_path(j))
    if j.duration <= 0:
        return fail(j, "That file is not a video or audio file we can read.")
    if j.duration > V.MAX_SECONDS + 5:
        return fail(j, "The video is %d minutes long. Videos can be up to %d minutes." % (round(j.duration / 60), V.MAX_SECONDS // 60))
    j.status = "queued"
    j.save(update_fields=["ext", "got", "size", "duration", "status"])
    log("job", j.id, "downloaded", got, "bytes")


def clean(segs):
    out, last, rep = [], "", 0
    for x in segs:
        t = re.sub(r"\s+", " ", x["t"]).strip()
        if not t:
            continue
        rep = rep + 1 if t == last else 0
        last = t
        if rep >= 2:                    # the same line again and again = the AI imagining speech in silence
            continue
        e = max(x["e"], x["s"] + 0.6)
        out.append({"s": round(x["s"], 2), "e": round(e, 2), "t": t})
    return out


def process(j):
    path = V.video_path(j)
    dur = probe(path)
    if dur <= 0:
        return fail(j, "That file is not a video or audio file we can read.")
    if dur > V.MAX_SECONDS + 5:
        return fail(j, "The video is %d minutes long. Videos can be up to %d minutes." % (round(dur / 60), V.MAX_SECONDS // 60))
    if V.site_minutes_today() + dur / 60 > V.SITE_MINUTES_DAY + 60:
        return fail(j, "Video Translate is very busy today. Please try again tomorrow.")
    j.duration, j.status, j.progress, j.error = dur, "working", 1, ""
    j.save(update_fields=["duration", "status", "progress", "error"])
    adir = os.path.join(V.jdir(j), "a")
    shutil.rmtree(adir, ignore_errors=True); os.makedirs(adir)
    r = subprocess.run(["nice", "-n", "15", "ffmpeg", "-nostdin", "-y", "-v", "error", "-i", path, "-t", str(V.MAX_SECONDS), "-vn", "-ac", "1", "-ar", "16000",
                        "-b:a", "32k", "-f", "segment", "-segment_time", str(PIECE), "-reset_timestamps", "1", os.path.join(adir, "p%03d.mp3")],
                       capture_output=True, text=True, timeout=1800)
    pieces = sorted(f for f in os.listdir(adir) if f.endswith(".mp3"))
    if r.returncode or not pieces:
        return fail(j, "This video has no sound we can read.")
    lang = "" if j.src_lang == "auto" else j.src_lang
    segs = []
    for n, f in enumerate(pieces):
        close_old_connections()
        if not Job.objects.filter(pk=j.pk).exists():
            log("job", j.id, "deleted while working"); return
        off = n * PIECE
        length = min(PIECE, max(1.0, dur - off))
        try:
            got, found = ai.transcribe(os.path.join(adir, f), length, lang or None)
            if not lang:
                found = (found or "").lower()[:8]
                if found == "hi":               # Pakistani and Indian speech sound the same - write it in Urdu script
                    found = "ur"
                    got, _ = ai.transcribe(os.path.join(adir, f), length, "ur")
                lang = found or "en"
        except ai.AIError as e:
            log("job", j.id, "AI:", str(e)[:200])
            return fail(j, "Could not write the subtitles right now. Please try again later.")
        for x in got:
            segs.append({"s": off + min(x["s"], length), "e": off + min(max(x["e"], x["s"]), length), "t": x["t"]})
        j.minutes += length / 60
        j.progress = max(1, min(99, int((n + 1) * 100 / len(pieces))))
        Job.objects.filter(pk=j.pk).update(progress=j.progress, minutes=j.minutes)
    segs = clean(segs)
    if lang == "pa":
        segs = [dict(x, t=to_shahmukhi(x["t"])) for x in segs]
    shutil.rmtree(adir, ignore_errors=True)
    if not segs:
        return fail(j, "No speech was found in this video.")
    j.segments, j.lang, j.status, j.progress, j.done_at = segs, lang, "ready", 100, timezone.now()
    j.save(update_fields=["segments", "lang", "status", "progress", "done_at", "minutes"])
    if j.want and j.want != lang and j.want in ai.LANGS:
        Track.objects.get_or_create(job=j, lang=j.want)
    notify(j.user, "\U0001F3AC Your subtitles are ready: %s" % j.title[:60], "/video-translate?id=%d" % j.id)
    log("job", j.id, "ready", len(segs), "lines", lang)


def do_track(t):
    j = t.job
    src = j.segments or []
    t.status, t.progress = "working", 1
    t.save(update_fields=["status", "progress"])
    out = []
    try:
        for i in range(0, len(src), BATCH):
            close_old_connections()
            part = [x["t"] for x in src[i:i + BATCH]]
            res = ai.translate_lines(part, t.lang, j.lang)
            miss = [k for k, v in enumerate(res) if not v]
            if miss:
                for k0 in range(0, len(miss), 10):
                    ks = miss[k0:k0 + 10]
                    again = ai.translate_lines([part[k] for k in ks], t.lang, j.lang)
                    for k, v in zip(ks, again):
                        res[k] = v
            for x, v in zip(src[i:i + BATCH], res):
                out.append({"s": x["s"], "e": x["e"], "t": v or x["t"]})
            Track.objects.filter(pk=t.pk).update(progress=max(1, min(99, int((i + BATCH) * 100 / max(1, len(src))))))
    except ai.AIError as e:
        log("track", t.id, "AI:", str(e)[:200])
        Track.objects.filter(pk=t.pk).update(status="failed")
        return
    if t.lang == "pa":
        out = [dict(x, t=to_shahmukhi(x["t"])) for x in out]
    t.segments, t.status, t.progress = out, "ready", 100
    t.save(update_fields=["segments", "status", "progress"])
    log("track", t.id, t.lang, "ready")


def tidy():
    now = timezone.now()
    for j in Job.objects.filter(video_gone=False, expires_at__lt=now):
        if j.status in ("uploading", "downloading", "queued", "working"):
            continue                                          # still being made
        if j.done_at and j.done_at > now - timedelta(minutes=30):
            continue                                          # finished late (long queue): keep it 30 minutes so it can be watched
        V.remove_files(j); Job.objects.filter(pk=j.pk).update(video_gone=True)
        log("job", j.id, "video deleted (2 hours)")
    old = now - timedelta(hours=3)
    for j in Job.objects.filter(status__in=("uploading", "downloading"), created_at__lt=old):
        V.remove_files(j); j.delete()
    for j in Job.objects.filter(status="failed", created_at__lt=now - timedelta(days=1)):
        V.remove_files(j); j.delete()
    for j in Job.objects.filter(created_at__lt=now - timedelta(days=V.KEEP_TEXT_DAYS)):
        V.remove_files(j); j.delete()
    Track.objects.filter(status="working").update(status="queued")     # a run that stopped half way: start that language again


class Command(BaseCommand):
    help = "Video Translate worker (run every minute by cron)."

    def handle(self, *a, **k):
        os.makedirs(V.vdir(), exist_ok=True)
        lock = open(os.path.join(V.vdir(), ".lock"), "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return
        socket.setdefaulttimeout(60)
        for j in Job.objects.filter(status="working"):
            fail(j, "Stopped half way. Please try again.")
        tidy()
        start = time.time()
        while time.time() - start < RUN_FOR:
            close_old_connections()
            j = Job.objects.filter(status="downloading").order_by("id").first()
            if j:
                download(j); continue
            j = Job.objects.filter(status="queued").order_by("id").first()
            if j:
                process(j); continue
            t = Track.objects.filter(status="queued", job__status="ready").select_related("job").order_by("id").first()
            if t:
                do_track(t); continue
            break
        tidy()
