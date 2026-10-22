"""My stickers (/api/notify/stickers/): each member's own stickers, kept on the server so they show on every phone.
mine/              GET my stickers | POST file = a still sticker made on the phone (PNG / WebP with a see-through background)
mine/<name>/       DELETE one
make/              POST clip (a short video) + overlay (PNG with the words) + start, dur, shape, cx, cy, cs -> an animated sticker
Also: photos sent in chats and groups now keep a see-through background and animation, so stickers look right.
(setup_xpertchat_v2)"""
import os
import re
import secrets
import shutil
import subprocess
import tempfile

from django.conf import settings
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

MAX_STICKERS = 40
MAX_STILL = 1536 * 1024
MAX_CLIP = 40 * 1024 * 1024
MAX_OUT = 1900 * 1024
def _enc():
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20)
        return "libwebp_anim" if "libwebp_anim" in r.stdout else "libwebp"
    except Exception:
        return "libwebp"


ENC = None
NAME = re.compile(r"^[a-f0-9]{20}\.(webp)$")


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _dir(u):
    d = os.path.join(str(settings.MEDIA_ROOT), "stickers", "u%d" % u.pk)
    os.makedirs(d, exist_ok=True)
    return d


def _url(u, name):
    return settings.MEDIA_URL.rstrip("/") + "/stickers/u%d/%s" % (u.pk, name)


def _list(u):
    d = _dir(u)
    names = [n for n in os.listdir(d) if NAME.match(n)]
    names.sort(key=lambda n: os.path.getmtime(os.path.join(d, n)), reverse=True)
    out = []
    for n in names:
        try:
            with open(os.path.join(d, n), "rb") as fh:
                head = fh.read(64)
            anim = b"ANIM" in head or b"ANMF" in head
        except OSError:
            anim = False
        out.append({"name": n, "url": _url(u, n), "anim": anim})
    return out


def _new_name():
    return secrets.token_hex(10) + ".webp"


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def mine(request):
    u = request.user
    if request.method == "GET":
        return Response({"stickers": _list(u), "max": MAX_STICKERS})
    if len(_list(u)) >= MAX_STICKERS:
        return _err("You have %d stickers. Remove some first." % MAX_STICKERS)
    f = request.FILES.get("file")
    if not f or f.size > MAX_STILL:
        return _err("Choose a sticker picture (up to 1.5 MB).")
    from PIL import Image
    try:
        im = Image.open(f); im.load()
    except Exception:
        return _err("That is not a picture we can read.")
    if im.format not in ("PNG", "WEBP"):
        return _err("Use a PNG or WebP sticker.")
    im = im.convert("RGBA"); im.thumbnail((512, 512))
    name = _new_name()
    im.save(os.path.join(_dir(u), name), "WEBP", quality=82, method=4)
    return Response({"name": name, "url": _url(u, name), "anim": False, "stickers": _list(u)}, status=201)


@api_view(["DELETE", "POST"])
@permission_classes([IsAuthenticated])
def mine_one(request, name):
    if not NAME.match(name or ""):
        return _err("Not found.", 404)
    p = os.path.join(_dir(request.user), name)
    if os.path.isfile(p):
        os.remove(p)
    return Response({"stickers": _list(request.user)})


def _num(v, lo, hi, d):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return d
    return max(lo, min(hi, v))


def _probe(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "default=nw=1", path],
                           capture_output=True, text=True, timeout=30)
        d = dict(x.split("=", 1) for x in r.stdout.split() if "=" in x)
        return int(d.get("width", 0)), int(d.get("height", 0)), float(d.get("duration", 0) or 0)
    except Exception:
        return 0, 0, 0


MASKS = {
    "circle": "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*lt(hypot(X-W/2,Y-H/2),W/2-3)'",
    "round": "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*lt(hypot(max(abs(X-W/2)-(W/2-63),0),max(abs(Y-H/2)-(H/2-63),0)),60)'",
    "full": "",
}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def make(request):
    """An animated sticker from a few seconds of video."""
    u, d = request.user, request.data
    if len(_list(u)) >= MAX_STICKERS:
        return _err("You have %d stickers. Remove some first." % MAX_STICKERS)
    clip = request.FILES.get("clip")
    if not clip or clip.size > MAX_CLIP:
        return _err("Choose a video clip (up to 40 MB).")
    if not shutil.which("ffmpeg"):
        return _err("Animated stickers are not switched on yet.", 503)
    tmp = tempfile.mkdtemp(prefix="xcstk")
    try:
        src = os.path.join(tmp, "in")
        with open(src, "wb") as out:
            for ch in clip.chunks():
                out.write(ch)
        vw, vh, dur = _probe(src)
        if not vw or not vh:
            return _err("That file is not a video we can read.")
        start = _num(d.get("start"), 0, max(0, dur - .5), 0)
        length = _num(d.get("dur"), 1, 6, 3)
        cs = int(_num(d.get("cs"), 16, min(vw, vh), min(vw, vh)))
        cx = int(_num(d.get("cx"), 0, vw - cs, (vw - cs) / 2))
        cy = int(_num(d.get("cy"), 0, vh - cs, (vh - cs) / 2))
        shape = d.get("shape") if d.get("shape") in MASKS else "circle"
        ov = request.FILES.get("overlay")
        ovp = ""
        if ov and ov.size < 3 * 1024 * 1024:
            ovp = os.path.join(tmp, "ov.png")
            with open(ovp, "wb") as out:
                for ch in ov.chunks():
                    out.write(ch)
        global ENC
        ENC = ENC or _enc()
        name = _new_name()
        dst = os.path.join(tmp, name)
        for size, fps, q in ((320, 12, 62), (288, 10, 48), (240, 9, 38)):
            chain = "[0:v]crop=%d:%d:%d:%d,scale=%d:%d:flags=lanczos,fps=%d,format=rgba" % (cs, cs, cx, cy, size, size, fps)
            if MASKS[shape]:
                chain += "," + MASKS[shape]
            cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % start, "-t", "%.2f" % length, "-i", src]
            if ovp:
                cmd += ["-i", ovp]
                graph = chain + "[v];[1:v]scale=%d:%d,format=rgba[o];[v][o]overlay=0:0:format=auto,format=rgba[out]" % (size, size)
            else:
                graph = chain + "[out]"
            cmd += ["-filter_complex", graph, "-map", "[out]", "-an", "-loop", "0", "-c:v", ENC, "-lossless", "0", "-quality", str(q), "-compression_level", "4", dst]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode != 0 or not os.path.isfile(dst):
                return _err("Could not make the sticker from this video (%s)." % (r.stderr.strip().splitlines() or ["unknown error"])[-1][:120])
            if os.path.getsize(dst) <= MAX_OUT:
                break
        if os.path.getsize(dst) > MAX_OUT:
            return _err("This clip makes a sticker that is too big. Choose a shorter part.")
        shutil.move(dst, os.path.join(_dir(u), name))
        return Response({"name": name, "url": _url(u, name), "anim": True, "stickers": _list(u)}, status=201)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- photos in chats and groups keep see-through and animation
def _keep(f, rel):
    from PIL import Image, ImageOps, ImageSequence
    im = Image.open(f)
    anim = bool(getattr(im, "is_animated", False)) and im.format in ("WEBP", "GIF", "PNG")
    alpha = "A" in im.getbands() or "transparency" in im.info
    if not anim and not alpha:
        return None
    if f.size > 2 * 1024 * 1024:
        raise ValueError("That photo is over 2 MB.")
    frames, durs = [], []
    for fr in ImageSequence.Iterator(im):
        x = fr.convert("RGBA")
        if not anim:
            x = ImageOps.exif_transpose(x)
        x.thumbnail((640, 640) if anim else (1280, 1280))
        frames.append(x); durs.append(int(fr.info.get("duration", 80) or 80))
        if len(frames) >= 150 or not anim:
            break
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if len(frames) > 1:
        frames[0].save(full, "WEBP", save_all=True, append_images=frames[1:], duration=durs, loop=0, quality=72, method=4)
    else:
        frames[0].save(full, "WEBP", quality=80, method=4)
    return rel


def _wrap(mod, make_rel):
    orig = getattr(mod, "_save_photo", None)
    if not orig or getattr(orig, "_xcstk", False):
        return

    def saver(f, key):
        rel = None
        try:
            rel = _keep(f, make_rel(key))
        except ValueError:
            raise
        except Exception:
            rel = None
        try:
            f.seek(0)
        except Exception:
            pass
        return rel or orig(f, key)
    saver._xcstk = True
    mod._save_photo = saver


try:
    from . import groups as _g, views as _v
    _wrap(_v, lambda k: "chat/%d/%s.webp" % (int(k), secrets.token_hex(12)))
    _wrap(_g, lambda k: "chat/%s/%s.webp" % (k, secrets.token_hex(12)))
except Exception:
    pass
