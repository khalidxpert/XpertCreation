"""One-time IRC pass for signed-in members: Ergo checks it with /opt/ergo/sso_auth.py (same secret). Valid for 60 seconds."""
import hashlib
import hmac
import os
import re
import time

from django.conf import settings
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
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


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify(request):
    """Only for the IRC server's check script (shared secret): is this XpertCreation username + password correct?"""
    sec = _secret()
    if not sec or not hmac.compare_digest(str(request.headers.get("X-IRC-Secret") or ""), sec):
        return Response({"ok": False}, status=403)
    acct, pw = str(request.data.get("account") or "").strip(), str(request.data.get("password") or "")
    if not acct or not pw:
        return Response({"ok": False})
    from django.contrib.auth import get_user_model
    for u in get_user_model().objects.filter(is_active=True, username__iexact=acct)[:1]:
        if irc_nick(u).lower() == acct.lower() and u.check_password(pw):
            return Response({"ok": True, "nick": irc_nick(u)})
    return Response({"ok": False})
