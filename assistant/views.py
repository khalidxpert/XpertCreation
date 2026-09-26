"""XpertCreation assistant: a chat helper for signed-in members, run on Cloudflare Workers AI's free
allowance. The conversation lives in the member's browser; the server keeps only a daily count.

Settings (.env): AI_PROVIDER=cloudflare, CF_AI_ACCOUNT_ID, CF_AI_TOKEN, and optionally
AI_MODEL (default @cf/meta/llama-3.3-70b-instruct-fp8-fast), AI_DAILY_LIMIT (per member, default 30),
AI_SITE_DAILY_LIMIT (all members together, default 1500)."""
import os

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import AssistantUse

SYSTEM = """You are the XpertCreation Assistant, a friendly helper for members of xpertcreation.com, a free platform from Lahore, Pakistan.

How to answer:
- Reply in the language the member uses: Urdu, English or Roman Urdu. Keep it clear and fairly short; use short lists when they help.
- Be honest. If you are not sure, say so. Do not invent facts, prices, laws or links.
- For health, legal, tax or money questions, give general information only and suggest a qualified professional for their own case. In an emergency, tell them to contact local emergency services.
- Never ask for passwords, card numbers, CNIC numbers or other private details, and tell members not to share them.
- Refuse to help with anything harmful, hateful, sexual, violent, or illegal, and with cheating or scams. Be polite when you refuse.
- You are an AI and you do not have access to members' accounts, chats or data on the site.

The site (suggest these when they fit the question):
- XpertAcademy (/academy/): free courses in Excel, Word, PowerPoint, VBA, Python, JavaScript, languages and Quranic Arabic, with certificates.
- Tools (/tools): 70+ free calculators and converters, prayer times, Qibla, Hijri dates, domain and DNS tools, business tools for staff and stock (/business).
- Connect (/people): professional profiles, skills, connections. Feed (/feed): posts. Jobs (/jobs): free job posting and applying.
- Chat (/chat), Pets (/pets): health records, QR tags, lost and found (/lost), free adoption (/adopt), vets (/vets).
- Shows (/shows): Pakistani and Indian dramas and films. Games (/games). Blood bank (/blood). Guide (/docs). Support (/support)."""

TOO_BUSY = "The assistant has used up today's free allowance for the whole site. Please try again tomorrow."


def _env(name, default=""):
    v = getattr(settings, name, "") or os.environ.get(name, "")
    if v:
        return v
    try:
        with open(os.path.join(str(settings.BASE_DIR), ".env")) as f:
            for line in f:
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return default


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


def _limits():
    try:
        per_user = int(_env("AI_DAILY_LIMIT", "30"))
    except ValueError:
        per_user = 30
    try:
        site = int(_env("AI_SITE_DAILY_LIMIT", "1500"))
    except ValueError:
        site = 1500
    return per_user, site


def _used(user):
    row = AssistantUse.objects.filter(user=user, day=timezone.localdate()).first()
    return row.count if row else 0


def _site_used():
    return AssistantUse.objects.filter(day=timezone.localdate()).aggregate(n=Sum("count"))["n"] or 0


def _ask_cloudflare(messages):
    acc, tok = _env("CF_AI_ACCOUNT_ID"), _env("CF_AI_TOKEN")
    model = _env("AI_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    if not acc or not tok:
        raise RuntimeError("not set up")
    r = requests.post("https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acc, model),
                      headers={"Authorization": "Bearer " + tok},
                      json={"messages": messages, "max_tokens": 700, "temperature": 0.6}, timeout=45)
    if r.status_code == 429 or "limit" in r.text.lower() and r.status_code >= 400:
        raise OverflowError(TOO_BUSY)
    d = r.json()
    if not d.get("success"):
        raise RuntimeError("provider error")
    out = (d.get("result") or {}).get("response")
    if isinstance(out, dict):
        out = out.get("content") or ""
    return str(out or "").strip()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def status(request):
    per_user, _ = _limits()
    return Response({"limit": per_user, "left": max(0, per_user - _used(request.user)),
                     "ready": bool(_env("CF_AI_ACCOUNT_ID") and _env("CF_AI_TOKEN"))})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request):
    u = request.user
    if getattr(u, "is_blocked", False) or not getattr(u, "is_email_verified", True):
        return Response({"detail": "Verify your email to use the assistant."}, status=403)
    per_user, site = _limits()
    if _used(u) >= per_user:
        return Response({"detail": "You have asked %d questions today. The assistant will be back for you tomorrow." % per_user, "left": 0}, status=429)
    if _site_used() >= site:
        return Response({"detail": TOO_BUSY, "left": 0}, status=429)
    if not cache.add("ai_busy:%d" % u.pk, 1, 3):          # one question at a time, a few seconds apart
        return Response({"detail": "One moment - the last answer is still on its way."}, status=429)
    raw = request.data.get("messages") or []
    if not isinstance(raw, list):
        return Response({"detail": "Nothing to answer."}, status=400)
    msgs, total = [], 0
    for m in reversed(raw[-12:]):                           # the newest turns, up to about 6000 letters
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            continue
        text = str(m.get("content") or "")[:2000]
        if total + len(text) > 6000:
            break
        msgs.insert(0, {"role": m["role"], "content": text})
        total += len(text)
    if not msgs or msgs[-1]["role"] != "user" or not msgs[-1]["content"].strip():
        return Response({"detail": "Write a question first."}, status=400)
    try:
        reply = _ask_cloudflare([{"role": "system", "content": SYSTEM}] + msgs)
    except OverflowError as e:
        return Response({"detail": str(e), "left": max(0, per_user - _used(u))}, status=429)
    except Exception:
        cache.delete("ai_busy:%d" % u.pk)
        return Response({"detail": "The assistant could not answer just now. Please try again in a minute."}, status=503)
    if not reply:
        reply = "Sorry, I could not think of an answer. Could you ask it another way?"
    row, _ = AssistantUse.objects.get_or_create(user=u, day=timezone.localdate())
    AssistantUse.objects.filter(pk=row.pk).update(count=F("count") + 1)
    return Response({"reply": reply, "left": max(0, per_user - row.count - 1)})


@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def usage(request):
    today = timezone.localdate()
    days = list(AssistantUse.objects.filter(day__gte=today - timezone.timedelta(days=29)).values("day")
                .annotate(n=Sum("count")).order_by("-day"))
    per_user, site = _limits()
    return Response({"today": _site_used(), "site_limit": site, "per_user_limit": per_user,
                     "model": _env("AI_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
                     "days": [{"day": str(d["day"]), "questions": d["n"]} for d in days],
                     "members_today": AssistantUse.objects.filter(day=today).count()})
