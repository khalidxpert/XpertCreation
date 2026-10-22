"""Talking to our LiveKit server: access tokens (JWT, HS256) and a few room commands.
Keys come from /etc/xpertcreation/live.json (made by the installer, readable by the website only) or settings.LIVE_CONF."""
import base64
import hashlib
import hmac
import json
import time
import urllib.request

from django.conf import settings

_CONF = None


def conf():
    global _CONF
    if _CONF is None:
        c = getattr(settings, "LIVE_CONF", None)
        if not c:
            with open("/etc/xpertcreation/live.json") as fh:
                c = json.load(fh)
        _CONF = c
    return _CONF


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def token(identity, name, room, publish=False, data=True, admin=False, ttl=6 * 3600, metadata=""):
    c = conf()
    now = int(time.time())
    grant = {"room": room, "roomJoin": True, "canSubscribe": True, "canPublish": bool(publish), "canPublishData": bool(data)}
    if admin:
        grant.update({"roomAdmin": True, "roomCreate": True})
    claims = {"iss": c["key"], "sub": identity, "name": name[:60], "nbf": now - 10, "exp": now + ttl, "video": grant, "metadata": metadata}
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    sig = _b64(hmac.new(c["secret"].encode(), (head + "." + body).encode(), hashlib.sha256).digest())
    return head + "." + body + "." + sig


def call(method, room, payload):
    """RoomService twirp call on the local LiveKit server. Returns the JSON answer, or None."""
    c = conf()
    url = c.get("api", "http://127.0.0.1:7880") + "/twirp/livekit.RoomService/" + method
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + token("server", "server", room, admin=True, ttl=120)})
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read().decode() or "{}")
    except Exception:
        return None


def ws_url():
    return conf().get("ws", "")
