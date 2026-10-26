"""Sign in with Google, Discord, Facebook, X or Telegram.

The site signs people in with a session cookie, so this is the plain
authorisation-code flow for the OAuth2 providers: send the browser to the
provider, take the code back, swap it for a token, read the profile, then
log the person in with the same checks the password login uses.

Two of them are special cases:

* Telegram has no redirect out. Its Login Widget posts the profile straight
  back with an HMAC-SHA256 signature made from the bot token, so there is
  nothing to exchange - only a signature to check.
* X requires PKCE, and returns no email address at all.
"""

import base64
import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import User

log = logging.getLogger(__name__)

TIMEOUT = 12

# Telegram and X have no address on file, but accounts here are keyed by
# email, so a stable placeholder is used. It is never emailed and never
# verifies anything.
PLACEHOLDER_DOMAIN = "users.xpertcreation.com"

ENDPOINTS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "profile": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
        "method": "POST",
    },
    "discord": {
        "authorize": "https://discord.com/api/oauth2/authorize",
        "token": "https://discord.com/api/oauth2/token",
        "profile": "https://discord.com/api/users/@me",
        "scope": "identify email",
        "method": "POST",
    },
    "facebook": {
        "authorize": "https://www.facebook.com/v21.0/dialog/oauth",
        "token": "https://graph.facebook.com/v21.0/oauth/access_token",
        "profile": "https://graph.facebook.com/me?fields=id,name,email",
        "scope": "email,public_profile",
        "method": "GET",
    },
    "x": {
        "authorize": "https://x.com/i/oauth2/authorize",
        "token": "https://api.x.com/2/oauth2/token",
        "profile": "https://api.x.com/2/users/me",
        "scope": "users.read tweet.read",
        "method": "POST",
        "pkce": True,
        "basic": True,
    },
}

OAUTH_PROVIDERS = tuple(ENDPOINTS)
PROVIDERS = OAUTH_PROVIDERS + ("telegram",)


def _conf(provider):
    return (getattr(settings, "SOCIAL_LOGIN", {}) or {}).get(provider) or {}


def _fail_url(reason=""):
    base = getattr(settings, "SOCIAL_LOGIN_FAIL",
                   "https://xpertcreation.com/login?social=error")
    return base + ("&reason=" + reason if reason else "")


def _done_url():
    return getattr(settings, "SOCIAL_LOGIN_DONE",
                   "https://xpertcreation.com/login?social=1")


def _ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _configured(provider):
    conf = _conf(provider)
    if provider == "telegram":
        return bool(conf.get("bot_token") and conf.get("bot_username"))
    return bool(conf.get("client_id") and conf.get("client_secret") and conf.get("redirect"))


def _pkce_pair():
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def _profile(provider, info):
    """(email, full name, provider says the email is verified)."""
    if provider == "x":
        data = info.get("data") or {}
        name = (data.get("name") or "").strip() or (data.get("username") or "").strip()
        return "", name, False

    email = (info.get("email") or "").strip().lower()
    if provider == "google":
        return email, (info.get("name") or "").strip(), bool(info.get("email_verified"))
    if provider == "facebook":
        # Facebook only returns an address it has already confirmed.
        return email, (info.get("name") or "").strip(), bool(email)
    # Discord only returns an email when the "email" scope was granted.
    name = (info.get("global_name") or info.get("username") or "").strip()
    return email, name, bool(info.get("verified"))


def _sign_in(request, provider, email, name, verified):
    """Shared tail: find or make the account, then log it in."""
    user = User.objects.filter(email=email).first()
    created = False

    if user is None:
        if not verified:
            return HttpResponseRedirect(_fail_url("unverified"))
        user = User(email=email, full_name=(name or "")[:120])
        user.set_unusable_password()      # signs in socially; there is no password
        user.is_email_verified = True
        user.signup_ip = _ip(request)
        user.signup_country = (request.META.get("HTTP_CF_IPCOUNTRY") or "")[:2].upper()
        user.save()
        created = True
        log.info("social signup via %s: %s", provider, email)

    if not user.is_active or user.is_blocked:
        return HttpResponseRedirect(_fail_url("blocked"))

    if not user.is_email_verified:
        if not verified:
            return HttpResponseRedirect(_fail_url("verify"))
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

    if not user.full_name and name:
        user.full_name = name[:120]
        user.save(update_fields=["full_name"])

    login(request, user)
    request.session.cycle_key()
    user.last_login_ip = _ip(request)
    user.save(update_fields=["last_login_ip"])

    return HttpResponseRedirect(_done_url() + ("&new=1" if created else ""))


@api_view(["GET"])
@permission_classes([AllowAny])
def providers(request):
    """Which buttons the login page should show."""
    return Response({p: _configured(p) for p in PROVIDERS})


@api_view(["GET"])
@permission_classes([AllowAny])
def start(request, provider):
    if provider not in OAUTH_PROVIDERS or not _configured(provider):
        log.warning("social start: %s is not configured", provider)
        return HttpResponseRedirect(_fail_url("not_configured"))

    state = secrets.token_urlsafe(24)
    # The state lives in the session, so a callback from somewhere else is
    # rejected. SameSite=Lax still sends the cookie on this top-level return.
    request.session["social_state"] = state
    request.session["social_provider"] = provider

    conf = _conf(provider)
    params = {
        "client_id": conf["client_id"],
        "redirect_uri": conf["redirect"],
        "response_type": "code",
        "scope": ENDPOINTS[provider]["scope"],
        "state": state,
    }

    if ENDPOINTS[provider].get("pkce"):
        verifier, challenge = _pkce_pair()
        request.session["social_verifier"] = verifier
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    if provider == "google":
        params["access_type"] = "online"
        params["prompt"] = "select_account"

    return HttpResponseRedirect(ENDPOINTS[provider]["authorize"] + "?" + urlencode(params))


def _telegram_callback(request):
    """Telegram Login Widget: check the signature, then sign in."""
    conf = _conf("telegram")
    token = conf.get("bot_token") or ""
    if not token:
        return HttpResponseRedirect(_fail_url("not_configured"))

    data = {k: v for k, v in request.GET.items() if k != "hash"}
    got = request.GET.get("hash") or ""
    if not got or not data.get("id"):
        return HttpResponseRedirect(_fail_url("state"))

    check = "\n".join("%s=%s" % (k, data[k]) for k in sorted(data))
    secret = hashlib.sha256(token.encode()).digest()
    want = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, got):
        log.warning("telegram callback: bad signature")
        return HttpResponseRedirect(_fail_url("state"))

    try:
        auth_date = int(data.get("auth_date") or 0)
    except (TypeError, ValueError):
        auth_date = 0
    if not auth_date or time.time() - auth_date > 86400:
        return HttpResponseRedirect(_fail_url("state"))

    name = ("%s %s" % (data.get("first_name", ""), data.get("last_name", ""))).strip()
    if not name:
        name = data.get("username", "")
    email = "tg%s@%s" % (data["id"], PLACEHOLDER_DOMAIN)

    return _sign_in(request, "telegram", email, name, True)


@api_view(["GET"])
@permission_classes([AllowAny])
def callback(request, provider):
    if provider == "telegram":
        return _telegram_callback(request)

    if provider not in OAUTH_PROVIDERS or not _configured(provider):
        return HttpResponseRedirect(_fail_url("not_configured"))

    if request.GET.get("error"):
        return HttpResponseRedirect(_fail_url("denied"))

    state = request.GET.get("state") or ""
    saved = request.session.pop("social_state", "")
    saved_provider = request.session.pop("social_provider", "")
    if not saved or state != saved or saved_provider != provider:
        log.warning("social callback: state mismatch for %s", provider)
        return HttpResponseRedirect(_fail_url("state"))

    code = request.GET.get("code") or ""
    if not code:
        return HttpResponseRedirect(_fail_url("code"))

    conf = _conf(provider)
    payload = {
        "client_id": conf["client_id"],
        "client_secret": conf["client_secret"],
        "redirect_uri": conf["redirect"],
        "grant_type": "authorization_code",
        "code": code,
    }

    if ENDPOINTS[provider].get("pkce"):
        verifier = request.session.pop("social_verifier", "")
        if not verifier:
            return HttpResponseRedirect(_fail_url("state"))
        payload["code_verifier"] = verifier

    auth = None
    if ENDPOINTS[provider].get("basic"):
        # Confidential client: X wants the credentials in the Basic header.
        payload.pop("client_secret", None)
        auth = (conf["client_id"], conf["client_secret"])

    try:
        if ENDPOINTS[provider]["method"] == "GET":
            token = requests.get(ENDPOINTS[provider]["token"], params=payload,
                                 headers={"Accept": "application/json"},
                                 timeout=TIMEOUT)
        else:
            token = requests.post(ENDPOINTS[provider]["token"], data=payload,
                                  headers={"Accept": "application/json"},
                                  auth=auth, timeout=TIMEOUT)
        token.raise_for_status()
        access = token.json().get("access_token")
        if not access:
            return HttpResponseRedirect(_fail_url("token"))

        prof = requests.get(
            ENDPOINTS[provider]["profile"],
            headers={"Authorization": "Bearer " + access},
            timeout=TIMEOUT,
        )
        prof.raise_for_status()
        info = prof.json()
    except Exception:
        log.exception("social token exchange failed for %s", provider)
        return HttpResponseRedirect(_fail_url("network"))

    email, name, verified = _profile(provider, info)

    if provider == "x":
        # X returns no address at all without elevated access, so a stable
        # placeholder keyed to the account keeps repeat sign ins on one row.
        data = info.get("data") or {}
        xid = str(data.get("id") or "")
        if not xid:
            return HttpResponseRedirect(_fail_url("noemail"))
        email = "x%s@%s" % (xid, PLACEHOLDER_DOMAIN)
        verified = True

    if not email:
        # Discord and Facebook need the "email" scope; Google with openid always sends it.
        return HttpResponseRedirect(_fail_url("noemail"))

    return _sign_in(request, provider, email, name, verified)
