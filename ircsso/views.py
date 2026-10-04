"""One-time IRC pass for signed-in members: Ergo checks it with /opt/ergo/sso_auth.py (same secret). Valid for 60 seconds."""
import hashlib
import hmac
import os
import re
import time

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

TTL = 60


def _secret():
    try:
        env = dict(re.findall(r"^(IRC_SSO_SECRET)=(.*)$", open(os.path.join(settings.BASE_DIR, ".env")).read(), re.M))
        return env.get("IRC_SSO_SECRET", "").strip()
    except Exception:
        return ""


def irc_nick(u):
    n = re.sub(r"[^A-Za-z0-9_\-\[\]\\`^{}|]", "", getattr(u, "username", "") or "")
    if not n or n[0].isdigit() or n[0] == "-":
        n = "u" + n
    if len(n) < 3:
        n = "member%d" % u.pk
    return n[:30]


def make_token(nick, secret, now=None):
    exp = int(now or time.time()) + TTL
    sig = hmac.new(secret.encode(), ("%s:%d" % (nick.lower(), exp)).encode(), hashlib.sha256).hexdigest()[:40]
    return "%d.%s" % (exp, sig)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def token(request):
    sec = _secret()
    if not sec:
        return Response({"detail": "Chat rooms are not set up yet."}, status=503)
    n = irc_nick(request.user)
    return Response({"nick": n, "token": make_token(n, sec), "ttl": TTL})
