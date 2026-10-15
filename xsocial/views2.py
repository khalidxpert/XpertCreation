"""/api/xsocial/ - step 2: block, mute, restrict, close friends, two-step sign in.
people/                GET   my blocked, muted, restricted and close-friends lists
people/<act>/          POST  {slug or id, on}  act = block | mute | restrict | close
rel/?slug=x            GET   my settings for that person (for the profile menu)
twostep/               GET / POST {on, password}
twostep/login/         POST  {ticket, code}  - finishes a sign in that asked for a code
twostep/resend/        POST  {ticket}"""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CloseFriend, LoginTicket, Mute, Restrict, TwoStep
from .views import _avatar, _err, _name, _slug, _txt

log = logging.getLogger("xsocial")
CODE_MIN, MAX_TRIES = 10, 5


def _who(u):
    return {"id": u.pk, "name": _name(u), "slug": _slug(u), "avatar": _avatar(u)}


def _person(d):
    from network.models import ProProfile
    U = get_user_model()
    s = str(d.get("slug") or "").strip().strip("/").split("/in/")[-1]
    if s:
        p = ProProfile.objects.filter(slug__iexact=s).select_related("user").first()
        return p.user if p else None
    try:
        return U.objects.filter(pk=int(d.get("id"))).first()
    except (TypeError, ValueError):
        return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def people(request):
    from notifications.models import ChatBlock
    u = request.user
    U = get_user_model()
    def lst(ids):
        return [_who(x) for x in U.objects.filter(pk__in=list(ids))]
    return Response({"blocked": lst(ChatBlock.objects.filter(blocker=u).values_list("blocked_id", flat=True)),
                     "muted": lst(Mute.objects.filter(user=u).values_list("target_id", flat=True)),
                     "restricted": lst(Restrict.objects.filter(user=u).values_list("target_id", flat=True)),
                     "close": lst(CloseFriend.objects.filter(owner=u).values_list("friend_id", flat=True))})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rel(request):
    from notifications.models import ChatBlock
    u, x = request.user, _person(request.GET)
    if not x:
        return _err("Not found.", 404)
    return Response({"id": x.pk, "me": x.pk == u.pk, "block": ChatBlock.objects.filter(blocker=u, blocked=x).exists(),
                     "mute": Mute.objects.filter(user=u, target=x).exists(), "restrict": Restrict.objects.filter(user=u, target=x).exists(),
                     "close": CloseFriend.objects.filter(owner=u, friend=x).exists()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def people_set(request, act):
    from notifications.models import ChatBlock
    u, x = request.user, _person(request.data)
    if act not in ("block", "mute", "restrict", "close"):
        return _err("Unknown.", 404)
    if not x:
        return _err("Not found.", 404)
    if x.pk == u.pk:
        return _err("That is you.")
    on = str(request.data.get("on")).lower() in ("true", "1")
    M = {"block": (ChatBlock, "blocker", "blocked"), "mute": (Mute, "user", "target"), "restrict": (Restrict, "user", "target"), "close": (CloseFriend, "owner", "friend")}[act]
    if on:
        if act == "close":
            from network.models import Connection
            if not Connection.objects.filter(Q(from_user=u, to_user=x) | Q(from_user=x, to_user=u), state="accepted").exists():
                return _err("Close friends must be your connections first.")
        M[0].objects.get_or_create(**{M[1]: u, M[2]: x})
        if act == "block":        # blocking ends the connection, follows and close-friends both ways
            try:
                from network.models import Connection, Follow
                Connection.objects.filter(Q(from_user=u, to_user=x) | Q(from_user=x, to_user=u)).delete()
                Follow.objects.filter(Q(follower=u, following=x) | Q(follower=x, following=u)).delete()
            except Exception:
                log.exception("block cleanup")
            CloseFriend.objects.filter(Q(owner=u, friend=x) | Q(owner=x, friend=u)).delete()
    else:
        M[0].objects.filter(**{M[1]: u, M[2]: x}).delete()
    return Response({"ok": True, act: on, "who": _who(x)})


# ---------------------------------------------------------------- two-step sign in
def _hash(code):
    return hmac.new(settings.SECRET_KEY.encode(), ("2step:" + code).encode(), hashlib.sha256).hexdigest()


def _send_code(user, code):
    try:
        from accounts import emails
        return emails._send(user.email, "XpertCreation: your sign-in code",
                            "Someone (hopefully you) signed in to your XpertCreation account with your password. Enter this code to finish signing in. "
                            "If it was not you, change your password now.", code, CODE_MIN)
    except Exception:
        log.exception("two-step code email")
        return False


def need_code(user, request):
    """Called by the sign-in view after the password is right. Returns a ticket when a code is needed, else None."""
    t = TwoStep.objects.filter(user=user, on=True).first()
    if not t and not (user.is_staff or user.is_superuser or getattr(user, "is_moderator", False)):   # the team: always
        return None
    code = "%06d" % secrets.randbelow(1000000)
    tk = LoginTicket.objects.create(user=user, token=secrets.token_urlsafe(24), code_hash=_hash(code),
                                    expires=timezone.now() + timedelta(minutes=CODE_MIN), sent_at=timezone.now())
    _send_code(user, code)
    LoginTicket.objects.filter(user=user, expires__lt=timezone.now() - timedelta(days=1)).delete()
    return tk.token


def _hint(email):
    a, _, d = (email or "").partition("@")
    return (a[:2] + "***@" + d) if d else ""


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def twostep(request):
    u = request.user
    t, _ = TwoStep.objects.get_or_create(user=u)
    if request.method == "POST":
        if not u.check_password(str(request.data.get("password") or "")):
            return _err("Password is not right.", 401)
        t.on = str(request.data.get("on")).lower() in ("true", "1"); t.save()
    return Response({"on": t.on, "email": _hint(u.email)})


@api_view(["POST"])
@permission_classes([AllowAny])
def twostep_login(request):
    tk = LoginTicket.objects.filter(token=str(request.data.get("ticket") or "")[:48], used=False).select_related("user").first()
    if not tk or tk.expires < timezone.now():
        return _err("This sign-in has expired. Sign in again.", 400)
    if tk.tries >= MAX_TRIES:
        return _err("Too many wrong codes. Sign in again.", 429)
    code = "".join(ch for ch in str(request.data.get("code") or "") if ch.isdigit())[:6]
    if not hmac.compare_digest(_hash(code), tk.code_hash):
        tk.tries += 1; tk.save(update_fields=["tries"])
        return _err("That code is not right. %d tries left." % (MAX_TRIES - tk.tries), 400)
    tk.used = True; tk.save(update_fields=["used"])
    user = tk.user
    if getattr(user, "is_blocked", False):
        return _err("This account is on hold. Contact support.", 403)
    login(request, user, backend=(getattr(settings, "AUTHENTICATION_BACKENDS", None) or ["django.contrib.auth.backends.ModelBackend"])[0])
    request.session.cycle_key()
    out = {"detail": "Signed in."}
    try:
        from accounts.views import client_ip
        from accounts.serializers import MeSerializer
        user.last_login_ip = client_ip(request); user.save(update_fields=["last_login_ip"])
        out["user"] = MeSerializer(user).data
    except Exception:
        out["user"] = {"id": user.pk, "email": user.email}
    return Response(out)


@api_view(["POST"])
@permission_classes([AllowAny])
def twostep_resend(request):
    tk = LoginTicket.objects.filter(token=str(request.data.get("ticket") or "")[:48], used=False).select_related("user").first()
    if not tk or tk.expires < timezone.now():
        return _err("This sign-in has expired. Sign in again.", 400)
    if (timezone.now() - tk.sent_at).total_seconds() < 45:
        return _err("Wait a little before asking for another code.", 429)
    code = "%06d" % secrets.randbelow(1000000)
    tk.code_hash, tk.sent_at, tk.tries, tk.expires = _hash(code), timezone.now(), 0, timezone.now() + timedelta(minutes=CODE_MIN)
    tk.save(update_fields=["code_hash", "sent_at", "tries", "expires"])
    _send_code(tk.user, code)
    return Response({"detail": "A new code is on its way."})
