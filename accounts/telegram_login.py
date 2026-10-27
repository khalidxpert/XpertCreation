"""Telegram sign-in through the bot, without the browser widget.

telegram.org is blocked on some networks, and the official Login Widget needs
both a script and an iframe from that domain, so on those connections the
button silently disappears. This route avoids the widget completely:

1. the site hands the browser a signed, short-lived token and a t.me link,
2. the person presses Start in Telegram,
3. the bot replies with a signed link back to the site,
4. that link performs the normal session login.

Nothing is stored between steps: every hop carries an HMAC made with
SECRET_KEY, so the bot needs no database and there is no polling.
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from urllib.parse import quote

import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .social import PLACEHOLDER_DOMAIN, _conf, _fail_url, _sign_in

log = logging.getLogger(__name__)

TIMEOUT = 12
TTL = 15 * 60          # the bot link stops working after 15 minutes
SITE = "https://xpertcreation.com"
API = SITE + "/api/auth/social/telegram"


def _bot():
    conf = _conf("telegram") or {}
    token = (conf.get("bot_token") or "").strip()
    username = (conf.get("bot_username") or "").strip().lstrip("@")
    return token, username


def _hmac(text):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, text.encode(), hashlib.sha256).hexdigest()[:16]


def _start_token():
    """40 hex chars: 8 for the timestamp + 16 random + 16 signature."""
    body = "%08x%s" % (int(time.time()), secrets.token_hex(8))
    return body + _hmac("start:" + body)


def _start_ok(value):
    if len(value) != 40:
        return False
    body, sig = value[:24], value[24:]
    if not hmac.compare_digest(sig, _hmac("start:" + body)):
        return False
    try:
        stamp = int(body[:8], 16)
    except ValueError:
        return False
    return 0 <= time.time() - stamp <= TTL


def _finish_url(token, chat_id, name):
    uid = str(chat_id)
    hexed = name.encode("utf-8").hex() if name else ""
    sig = _hmac("finish:%s|%s|%s" % (uid, hexed, token))
    return "%s/finish/?k=%s&u=%s&n=%s&h=%s" % (API, token, uid, hexed, sig)


def _send(chat_id, text, button_url=None):
    token, _ = _bot()
    if not token:
        return
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if button_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": "Login complete karo", "url": button_url}]]
        }
    try:
        requests.post(
            "https://api.telegram.org/bot%s/sendMessage" % token,
            data=payload,
            timeout=TIMEOUT,
        )
    except Exception:
        log.exception("telegram: sendMessage failed")


def hook_path():
    """The webhook address hides the bot token behind a hash."""
    token, _ = _bot()
    return hashlib.sha256(("hook:" + token).encode()).hexdigest()[:24]


@api_view(["GET"])
@permission_classes([AllowAny])
def start(request):
    """Hand the browser a t.me link carrying a signed token."""
    token, username = _bot()
    if not token or not username:
        return Response({"error": "not_configured"}, status=400)
    link = "https://t.me/%s?start=%s" % (username, _start_token())
    return Response({"url": link})


@csrf_exempt
def hook(request, secret):
    """Telegram posts updates here. Reply with a signed login link."""
    token, _ = _bot()
    if not token or secret != hook_path():
        return HttpResponse(status=404)

    try:
        update = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return HttpResponse(status=400)

    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id or not text.startswith("/start"):
        return HttpResponse("ok", content_type="text/plain")

    parts = text.split(None, 1)
    key = parts[1].strip() if len(parts) > 1 else ""
    if not _start_ok(key):
        _send(chat_id, "Ye link expire ho gaya. Site par ja ke dobara "
                       "\"Continue with Telegram\" dabayein.")
        return HttpResponse("ok", content_type="text/plain")

    name = " ".join(
        x for x in (chat.get("first_name"), chat.get("last_name")) if x
    ).strip()
    _send(
        chat_id,
        "Assalam o alaikum%s! Login mukammal karne ke liye neeche wala "
        "button dabayein." % ((" " + name) if name else ""),
        button_url=_finish_url(key, chat_id, name),
    )
    return HttpResponse("ok", content_type="text/plain")


@api_view(["GET"])
@permission_classes([AllowAny])
def finish(request):
    """The link the bot sent: verify it, then sign the person in."""
    key = request.GET.get("k") or ""
    uid = request.GET.get("u") or ""
    hexed = request.GET.get("n") or ""
    sig = request.GET.get("h") or ""

    if not _start_ok(key) or not uid.isdigit():
        return _fail_url("state")

    if not hmac.compare_digest(sig, _hmac("finish:%s|%s|%s" % (uid, hexed, key))):
        log.warning("telegram login: signature mismatch")
        return _fail_url("state")

    try:
        name = bytes.fromhex(hexed).decode("utf-8") if hexed else ""
    except ValueError:
        name = ""

    email = "tg%s@%s" % (uid, PLACEHOLDER_DOMAIN)
    return _sign_in(request, "telegram", email, name, True)
