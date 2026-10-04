"""Every minute: convert new uploads with ffmpeg (H.264 + AAC, up to 720p, max 60 s, web-ready), make a cover picture,
upload both to the upload worker (Cloudflare R2), then publish or send to review."""
import json
import os
import re
import subprocess
import tempfile
import urllib.request
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from clips.models import Clip
from clips.views import notify, trusted


def _env():
    try:
        return dict(re.findall(r"^(WORKER_UPLOAD_[A-Z_]+)=(.*)$", open(os.path.join(settings.BASE_DIR, ".env")).read(), re.M))
    except Exception:
        return {}


def _send(path, field, endpoint, mime):
    e = _env(); url, tok = (e.get("WORKER_UPLOAD_URL") or "").strip().rstrip("/"), (e.get("WORKER_UPLOAD_TOKEN") or "").strip()
    b = uuid.uuid4().hex; data = open(path, "rb").read()
    body = ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (b, field, os.path.basename(path), mime)).encode() + data + ("\r\n--%s--\r\n" % b).encode()
    req = urllib.request.Request(url + "/" + endpoint, data=body, headers={"X-Upload-Token": tok, "Origin": "https://xpertcreation.com",
                                 "Content-Type": "multipart/form-data; boundary=" + b, "User-Agent": "XpertCreation/1.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=180).read().decode())
    if not d.get("ok"):
        raise RuntimeError("worker said no")
    return d.get("url"), d.get("key")


class Command(BaseCommand):
    help = "Process uploaded clips."

    def handle(self, *a, **o):
        done = 0
        for c in Clip.objects.filter(status="processing").order_by("id")[:3]:
            src = c.src_path
            if not src or not os.path.exists(src):
                c.status, c.note = "failed", "The upload was lost. Please try again."; c.save(); continue
            tmp = tempfile.mkdtemp(prefix="clip"); out, thumb = os.path.join(tmp, "clip.mp4"), os.path.join(tmp, "cover.jpg")
            try:
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", src], capture_output=True, text=True, timeout=60)
                dur = float((probe.stdout or "0").strip() or 0)
                if dur <= 0.5:
                    raise ValueError("That file does not look like a video.")
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-t", "60", "-vf", "scale='if(gt(iw,ih),min(1280,iw),min(720,iw))':-2,fps=30",
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-ac", "2",
                                "-movflags", "+faststart", out], check=True, timeout=600)
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(min(1.0, dur / 2)), "-i", out, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", thumb], check=True, timeout=120)
                vurl, vkey = _send(out, "video", "video", "video/mp4")
                turl, _ = _send(thumb, "avatar", "avatar", "image/jpeg")
                live = trusted(c.user) and not c.note
                c.video_url, c.video_key, c.thumb_url, c.duration = vurl, vkey or "", turl or "", min(dur, 60)
                c.status = "published" if live else "pending"; c.save()
                notify(c.user, "Your clip is live. \U0001F3AC" if live else "Your clip is ready and waiting for a quick review.", "/clips?id=%d" % c.id if live else "/clips?mine=1")
                done += 1
            except ValueError as e:
                c.status, c.note = "failed", str(e)[:300]; c.save(); notify(c.user, "Your clip could not be posted: %s" % c.note, "/clips?mine=1")
            except Exception as e:
                c.status, c.note = "failed", "We could not prepare that video. Please try another file."; c.save()
                self.stderr.write("clip %d: %s" % (c.id, e)); notify(c.user, "Your clip could not be posted. Please try another video file.", "/clips?mine=1")
            finally:
                for p in (src, out, thumb):
                    try: os.remove(p)
                    except Exception: pass
                try: os.rmdir(tmp)
                except Exception: pass
        self.stdout.write("clips processed: %d" % done)
