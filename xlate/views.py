"""Translate a post or message into the reader's language with Cloudflare Workers AI (Llama 3.3 70B). Saved, rate limited."""
import hashlib
import json
import os
import re
import urllib.request

from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Translation

LANGS = {"ur": "Urdu", "en": "English", "ar": "Arabic", "hi": "Hindi", "pa": "Punjabi (Shahmukhi script)", "ps": "Pashto", "sd": "Sindhi",
         "fa": "Persian", "bn": "Bengali", "zh": "Chinese (Simplified)", "tr": "Turkish", "de": "German", "fr": "French", "es": "Spanish",
         "no": "Norwegian", "ru": "Russian", "id": "Indonesian", "ms": "Malay"}
MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


def _env():
    try:
        return dict(re.findall(r"^(CF_AI_[A-Z_]+)=(.*)$", open(os.path.join(settings.BASE_DIR, ".env")).read(), re.M))
    except Exception:
        return {}


def _ai(text, target):
    e = _env(); acc, tok = (e.get("CF_AI_ACCOUNT_ID") or "").strip(), (e.get("CF_AI_TOKEN") or "").strip()
    msgs = [{"role": "system", "content": "You are a professional translator. Translate the user's text into %s. Keep the meaning, tone, line breaks, "
                                          "names, links, @mentions and #hashtags exactly as they are. Reply with the translation only, nothing else." % LANGS[target]},
            {"role": "user", "content": text}]
    req = urllib.request.Request("https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acc, MODEL),
                                 data=json.dumps({"messages": msgs, "max_tokens": min(2000, 200 + len(text) * 3)}).encode(),
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json", "User-Agent": "XpertCreation/1.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return ((d.get("result") or {}).get("response") or "").strip()


def _ip(request):
    return (request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or "")[:64]


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def translate(request):
    if request.method == "GET":
        return Response({"languages": [{"code": k, "name": v.split(" (")[0]} for k, v in LANGS.items()]})
    text = str(request.data.get("text") or "").strip()[:3000]; to = str(request.data.get("to") or "")
    if not text or to not in LANGS:
        return Response({"detail": "Nothing to translate."}, status=400)
    key = hashlib.sha256((to + "\n" + text).encode()).hexdigest()
    t = Translation.objects.filter(key=key).first()
    if t:
        return Response({"text": t.text, "to": to, "saved": True})
    who = ("u%d" % request.user.pk) if request.user.is_authenticated else ("ip" + _ip(request))
    limit = 60 if request.user.is_authenticated else 15
    n = cache.get_or_set("xlate:" + who, 0, 600)
    if n >= limit:
        return Response({"detail": "Too many translations. Please wait a few minutes."}, status=429)
    cache.incr("xlate:" + who)
    try:
        out = _ai(text, to)
    except Exception:
        return Response({"detail": "Translation is not available right now. Please try again."}, status=503)
    if not out:
        return Response({"detail": "Translation is not available right now. Please try again."}, status=503)
    Translation.objects.get_or_create(key=key, defaults={"target": to, "text": out})
    return Response({"text": out, "to": to, "saved": False})
