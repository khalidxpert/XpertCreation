"""Usernames: sign in with email or username, a live 'is it free?' check, set or change your username,
and 'forgot username' (sent to the account's email). Usernames are stored lowercase: 3-20 letters, numbers or _."""
import re
import unicodedata

from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User

RE = re.compile(r"^[a-z0-9_]{3,20}$")
RESERVED = {"admin", "administrator", "root", "support", "help", "official", "xpertcreation", "xpert", "moderator", "mod",
            "system", "staff", "team", "info", "contact", "security", "api", "login", "register", "account", "null", "none",
            "everyone", "all", "here", "bot", "xpertbot", "owner", "khalid_official"}
NEUTRAL = {"detail": "If this email has an account, we have sent its username to it."}


def clean(v):
    return str(v or "").strip().lstrip("@").lower()


def problem(name, user=None):
    """None if the username can be used, otherwise a short reason."""
    if not RE.match(name):
        return "Use 3 to 20 letters, numbers or _ (no spaces)."
    if name in RESERVED or name.isdigit():
        return "That username isn't available."
    qs = User.objects.filter(username__iexact=name)
    if user is not None:
        qs = qs.exclude(pk=user.pk)
    return "That username is taken." if qs.exists() else None


def suggest(base_text, user=None):
    """A free username from a name or an email: 'Syed Khalid' -> syed_khalid, syed_khalid2, ..."""
    t = unicodedata.normalize("NFKD", str(base_text or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:16] or "member"
    if len(t) < 3:
        t = (t + "_xc")[:16]
    cand, i = t, 1
    while problem(cand, user):
        i += 1
        cand = "%s%d" % (t[:20 - len(str(i))], i)
        if i > 999:
            return None
    return cand


def email_for(identifier):
    """Email or username in, the account's email out (or the input unchanged if no such username)."""
    v = str(identifier or "").strip()
    if v.startswith("@"):                     # "@khalid" is a username, not an email
        v = v[1:]
    elif "@" in v:
        return v.lower()
    u = User.objects.filter(username__iexact=clean(v)).only("email").first()
    return u.email if u else "unknown-user@invalid.invalid"


@api_view(["GET"])
@permission_classes([AllowAny])
def check(request):
    name = clean(request.GET.get("u"))
    p = problem(name, request.user if request.user.is_authenticated else None)
    return Response({"username": name, "ok": p is None, "detail": p or "Available", "suggestion": None if p is None else suggest(name)})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def mine(request):
    """GET: your username (a suggestion if you have none). POST {username}: set or change it (once a day at most)."""
    u = request.user
    if request.method == "GET":
        return Response({"username": u.username or "", "suggestion": None if u.username else suggest(u.full_name or u.email.split("@")[0], u)})
    name = clean(request.data.get("username"))
    p = problem(name, u)
    if p:
        return Response({"detail": p}, status=status.HTTP_400_BAD_REQUEST)
    key = "uname-change:%d" % u.pk
    if u.username == name:
        return Response({"username": name})
    if u.username and cache.get(key):
        return Response({"detail": "You can change your username once a day."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        User.objects.filter(pk=u.pk).update(username=name)
    except IntegrityError:
        return Response({"detail": "That username is taken."}, status=status.HTTP_400_BAD_REQUEST)
    cache.set(key, 1, 86400)
    return Response({"username": name})


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot(request):
    """{email}: the account's username is emailed to it. Always the same answer, so it can't be used to test emails."""
    email = str(request.data.get("email") or "").strip().lower()
    ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
    if not cache.add("uname-forgot:%s" % ip, 1, 60) or "@" not in email:
        return Response(NEUTRAL)
    u = User.objects.filter(email=email, is_active=True, is_blocked=False).first()
    if u:
        if not u.username:
            name = suggest(u.full_name or email.split("@")[0], u)
            if name:
                User.objects.filter(pk=u.pk).update(username=name); u.username = name
        try:
            from . import emails
            brand = getattr(emails, "BRAND", "XpertCreation")
            intro = "You asked for your username. You can sign in with it or with this email address."
            box = ('<p style="font-size:14px;line-height:1.5;margin:0 0 12px">%s</p><div style="font-size:24px;font-weight:700;text-align:center;'
                   'padding:16px;background:#F6F7FB;border-radius:12px;border:1px solid #E4E8F2">@%s</div>') % (intro, u.username)
            html = emails._WRAP.format(brand=brand, ttl=0, body=box)
            msg = EmailMultiAlternatives(subject="%s: your username" % brand, body="%s\n\n%s\n\nUsername: @%s" % (brand, intro, u.username),
                                         from_email=emails._from(), to=[u.email])
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=True)
        except Exception:
            pass
    return Response(NEUTRAL)
