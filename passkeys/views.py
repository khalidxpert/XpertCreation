"""Passkeys (/api/passkey/): sign in with fingerprint, face or phone screen lock instead of a password.
mine/                  my passkeys                     <id>/ DELETE   remove one
register/options|verify   add a passkey (signed in)
login/options|verify      sign in with a passkey (no password, counts as two-step too)"""
import json
import re

from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Passkey

from django.conf import settings

RP_ID = getattr(settings, "PASSKEY_RP_ID", "xpertcreation.com")
RP_NAME = "XpertCreation"
ORIGINS = getattr(settings, "PASSKEY_ORIGINS", ["https://xpertcreation.com", "https://www.xpertcreation.com"])
MAX_KEYS = 10


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _ip(request):
    try:
        from accounts.views import client_ip
        return client_ip(request)
    except Exception:
        return request.META.get("REMOTE_ADDR", "")


def _slow(request, kind, n=20):
    k = "pk:%s:%s" % (kind, _ip(request))
    c = cache.get(k, 0)
    if c >= n:
        return True
    cache.set(k, c + 1, 60)
    return False


def _device(request):
    ua = request.META.get("HTTP_USER_AGENT", "")
    for k, v in (("Android", "Android phone"), ("iPhone", "iPhone"), ("iPad", "iPad"), ("Windows", "Windows PC"), ("Macintosh", "Mac"), ("CrOS", "Chromebook"), ("Linux", "Linux PC")):
        if k in ua:
            return v
    return "This device"


def _row(p):
    return {"id": p.id, "name": p.name or "Passkey", "created": p.created_at.isoformat(), "last_used": p.last_used.isoformat() if p.last_used else None}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    return Response({"keys": [_row(p) for p in request.user.passkeys.all()]})


@api_view(["DELETE", "POST"])
@permission_classes([IsAuthenticated])
def remove(request, pk):
    n, _ = Passkey.objects.filter(pk=pk, user=request.user).delete()
    return Response({"ok": bool(n)}) if n else _err("Passkey not found.", 404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reg_options(request):
    from webauthn import generate_registration_options, options_to_json
    from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
    from webauthn.helpers.structs import AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor, ResidentKeyRequirement, UserVerificationRequirement
    u = request.user
    if u.passkeys.count() >= MAX_KEYS:
        return _err("You already have %d passkeys. Remove one first." % MAX_KEYS)
    label = getattr(u, "username", "") or u.email
    o = generate_registration_options(
        rp_id=RP_ID, rp_name=RP_NAME, user_id=("xc%d" % u.pk).encode(), user_name=label,
        user_display_name=(getattr(u, "full_name", "") or label)[:60],
        authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED, user_verification=UserVerificationRequirement.PREFERRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(p.cred_id)) for p in u.passkeys.all()])
    request.session["pk_reg"] = bytes_to_base64url(o.challenge)
    return Response(json.loads(options_to_json(o)))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reg_verify(request):
    from webauthn import verify_registration_response
    from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
    ch = request.session.pop("pk_reg", None)
    if not ch:
        return _err("That took too long. Tap Add a passkey again.")
    cred = request.data.get("credential")
    try:
        v = verify_registration_response(credential=cred, expected_challenge=base64url_to_bytes(ch), expected_rp_id=RP_ID, expected_origin=ORIGINS)
    except Exception as e:
        return _err("Your device's passkey could not be checked (%s). Try again." % str(e)[:120])
    cid = bytes_to_base64url(v.credential_id)
    if Passkey.objects.filter(cred_id=cid).exists():
        return _err("This passkey is already saved.")
    tr = ",".join(str(x) for x in ((cred or {}).get("response") or {}).get("transports") or [])[:120]
    name = re.sub(r"\s+", " ", str(request.data.get("name") or "")).strip()[:60] or _device(request)
    p = Passkey.objects.create(user=request.user, cred_id=cid, public_key=bytes_to_base64url(v.credential_public_key), sign_count=v.sign_count, name=name, transports=tr)
    try:
        from notifications.views import notify
        notify(request.user, "security", "\U0001F511 A passkey was added to your account (%s). If this wasn't you, remove it on the Safety page." % name, "/safety#passkeys")
    except Exception:
        pass
    return Response(_row(p), status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_options(request):
    from webauthn import generate_authentication_options, options_to_json
    from webauthn.helpers import bytes_to_base64url
    from webauthn.helpers.structs import UserVerificationRequirement
    if _slow(request, "lo"):
        return _err("Too many tries. Wait a minute.", 429)
    o = generate_authentication_options(rp_id=RP_ID, user_verification=UserVerificationRequirement.PREFERRED)
    request.session["pk_login"] = bytes_to_base64url(o.challenge)
    return Response(json.loads(options_to_json(o)))


@api_view(["POST"])
@permission_classes([AllowAny])
def login_verify(request):
    from webauthn import verify_authentication_response
    from webauthn.helpers import base64url_to_bytes
    if _slow(request, "lv"):
        return _err("Too many tries. Wait a minute.", 429)
    ch = request.session.pop("pk_login", None)
    cred = request.data.get("credential") or {}
    if not ch:
        return _err("That took too long. Tap Sign in with a passkey again.")
    p = Passkey.objects.select_related("user").filter(cred_id=str(cred.get("id") or cred.get("rawId") or "")[:400]).first()
    if not p:
        return _err("This passkey is not linked to any XpertCreation account. Sign in with your password, then add it on the Safety page.", 404)
    try:
        v = verify_authentication_response(credential=cred, expected_challenge=base64url_to_bytes(ch), expected_rp_id=RP_ID, expected_origin=ORIGINS,
                                           credential_public_key=base64url_to_bytes(p.public_key), credential_current_sign_count=p.sign_count)
    except Exception as e:
        return _err("The passkey could not be checked (%s)." % str(e)[:120], 401)
    u = p.user
    if not u.is_active or getattr(u, "is_blocked", False):
        return _err("This account is on hold. Contact support.", 403)
    if hasattr(u, "is_email_verified") and not u.is_email_verified:
        return _err("Confirm your email before signing in.", 403)
    p.sign_count, p.last_used = v.new_sign_count, timezone.now()
    p.save(update_fields=["sign_count", "last_used"])
    login(request, u, backend="django.contrib.auth.backends.ModelBackend")
    request.session.cycle_key()
    try:
        u.last_login_ip = _ip(request); u.save(update_fields=["last_login_ip"])
    except Exception:
        pass
    out = {"detail": "Signed in with a passkey."}
    try:
        from accounts.serializers import MeSerializer
        out["user"] = MeSerializer(u).data
    except Exception:
        out["user"] = {"email": u.email}
    return Response(out)
