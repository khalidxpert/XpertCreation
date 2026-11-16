"""XpertCreation assistant: a chat helper for signed-in members, run on Cloudflare Workers AI's free
allowance. The conversation lives in the member's browser; the server keeps only a daily count.

Settings (.env): AI_PROVIDER=cloudflare, CF_AI_ACCOUNT_ID, CF_AI_TOKEN, and optionally
AI_MODEL (default @cf/meta/llama-3.3-70b-instruct-fp8-fast), AI_DAILY_LIMIT (per member, default 30),
AI_SITE_DAILY_LIMIT (all members together, default 1500)."""
import os
import re  # article writer

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
- Tools (/tools): 102 free calculators and converters, prayer times, Qibla, Hijri dates, domain and DNS tools, business tools for staff and stock (/business).
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


# ---------------------------------------------------------------- article writer: a heading in, a full article out
# v2: it also makes a cover picture (FLUX on Workers AI) that the form attaches as the article cover.
# The member gives a heading; the model writes a complete article draft that fills the Articles form, where the
# member reads, edits and publishes it. Long answers run in a background thread (results in the shared cache),
# so no web timeout cuts them off. One article costs ARTICLE_COST of the member's daily assistant questions.
import threading as _thr
import uuid as _uuid

ARTICLE_COST = 5
ARTICLE_DAY_MAX = 5           # articles a member can draft per day

ARTICLE_SYSTEM = """You are an expert writer for XpertConnect, the professional network on xpertcreation.com, used by people worldwide.
The member gives you a heading. Write a complete, well-researched, comprehensive article on it.

Structure:
- First line: a clear, attractive title (no label like "Title:").
- An introduction paragraph that explains why the topic matters.
- 5 to 8 sections. Each section starts with a short heading on its own line, followed by 1 to 3 solid paragraphs.
  Use practical examples, steps, tips, pros and cons, or common mistakes where they fit.
- Where a list helps, put each item on its own line starting with "• ".
- A conclusion paragraph with the key takeaways.

Rules:
- Plain text only. Do NOT use markdown: no #, no **, no tables. Leave one empty line between paragraphs and after headings.
- Be accurate and honest. Do not invent statistics, quotes, studies, prices, laws or links. If a fact may change or depends on the country, say so in general words.
- For health, legal, tax or money topics, give general information and suggest a qualified professional for personal decisions.
- Neutral, helpful, professional tone. No hateful, sexual, violent or illegal content, and no content that attacks real people.
- Write in the language asked for. For Urdu, write proper Urdu in Urdu script (not Roman Urdu)."""

LENGTHS = {"short": 600, "medium": 1000, "long": 1500}
LANGS = {"en": "English", "ur": "Urdu (Urdu script)", "ar": "Arabic", "fr": "French", "de": "German", "es": "Spanish", "no": "Norwegian"}


def _clean_article(text):
    out = []
    for line in str(text or "").replace("\r", "").split("\n"):
        s = line.strip()
        s = re.sub(r"^#{1,6}\s*", "", s)                  # markdown headings -> plain heading lines
        s = s.replace("**", "").replace("__", "")
        s = re.sub(r"^[\-\*]\s+", "• ", s)               # "- item" -> "• item"
        s = re.sub(r"^(Title|Heading)\s*:\s*", "", s, flags=re.I)
        out.append(s)
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return body


IMAGE_MODEL_DEFAULT = "@cf/black-forest-labs/flux-1-schnell"
IMAGE_RULES = ("editorial magazine cover illustration, symbolic and thoughtful, professional, high quality, "
               "no text, no letters, no words, no logos, no watermarks, no flags, no identifiable real people, "
               "no gore, no blood, no injuries, nothing graphic")


def _cf_run(model, payload, timeout):
    acc, tok = _env("CF_AI_ACCOUNT_ID"), _env("CF_AI_TOKEN")
    if not acc or not tok:
        raise RuntimeError("not set up")
    r = requests.post("https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acc, model),
                      headers={"Authorization": "Bearer " + tok}, json=payload, timeout=timeout)
    if r.status_code == 429 or "limit" in r.text.lower() and r.status_code >= 400:
        raise OverflowError(TOO_BUSY)
    d = r.json()
    if not d.get("success"):
        raise RuntimeError("provider error")
    return d.get("result") or {}


def _cover_image(topic, box):
    """A cover picture for the heading: a short English scene description first (any heading language), then FLUX."""
    try:
        model = _env("AI_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
        res = _cf_run(model, {"messages": [
            {"role": "system", "content": "You write one short English sentence (max 40 words) describing a calm, symbolic picture for a "
                                          "magazine cover about the topic. Describe only what is seen. No text in the picture, no real or "
                                          "famous people, no flags, nothing violent or graphic. Reply with the sentence only."},
            {"role": "user", "content": topic}], "max_tokens": 90, "temperature": 0.7}, 40)
        scene = res.get("response")
        if isinstance(scene, dict):
            scene = scene.get("content") or ""
        scene = re.sub(r"\s+", " ", str(scene or topic)).strip().strip('"')[:300]
        img = _cf_run(_env("AI_IMAGE_MODEL", IMAGE_MODEL_DEFAULT), {"prompt": scene + ". " + IMAGE_RULES, "steps": 6}, 90).get("image")
        if img and len(img) < 4 * 1024 * 1024:
            box["image"] = "data:image/jpeg;base64," + img
    except Exception:
        pass


def _article_job(key, uid, topic, lang, words, with_image=True):
    box, it = {}, None
    if with_image:
        it = _thr.Thread(target=_cover_image, args=(topic, box), daemon=True)
        it.start()
    try:
        prompt = ("Heading: %s\nLanguage: %s\nLength: about %d words.\nWrite the full article now."
                  % (topic, LANGS.get(lang, "English"), words))
        acc, tok = _env("CF_AI_ACCOUNT_ID"), _env("CF_AI_TOKEN")
        model = _env("AI_ARTICLE_MODEL", "") or _env("AI_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
        if not acc or not tok:
            raise RuntimeError("not set up")
        r = requests.post("https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acc, model),
                          headers={"Authorization": "Bearer " + tok},
                          json={"messages": [{"role": "system", "content": ARTICLE_SYSTEM}, {"role": "user", "content": prompt}],
                                "max_tokens": min(4000, int(words * 2.2) + 400), "temperature": 0.6}, timeout=170)
        if r.status_code == 429 or "limit" in r.text.lower() and r.status_code >= 400:
            raise OverflowError(TOO_BUSY)
        d = r.json()
        if not d.get("success"):
            raise RuntimeError("provider error")
        out = (d.get("result") or {}).get("response")
        if isinstance(out, dict):
            out = out.get("content") or ""
        body = _clean_article(out)
        lines = body.split("\n")
        title = lines[0].strip()[:160] if lines else topic
        rest = "\n".join(lines[1:]).strip()
        if len(rest.split()) < 80:
            raise RuntimeError("too short")
        if it is not None:
            cache.set(key, {"state": "working", "stage": "image"}, 3600)
            it.join(100)
        cache.set(key, {"state": "done", "title": title or topic[:160], "body": rest[:40000], "image": box.get("image", "")}, 3600)
        row, _ = AssistantUse.objects.get_or_create(user_id=uid, day=timezone.localdate())
        AssistantUse.objects.filter(pk=row.pk).update(count=F("count") + ARTICLE_COST)
    except OverflowError as e:
        cache.set(key, {"state": "error", "detail": str(e)}, 3600)
    except Exception:
        cache.set(key, {"state": "error", "detail": "The writer could not finish this article just now. Please try again in a minute."}, 3600)
    finally:
        cache.delete("ai_art_busy:%d" % uid)
        try:
            from django.db import connection
            connection.close()
        except Exception:
            pass


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def article(request):
    """Start writing: {topic, lang, length} -> {job}. Poll article/<job>/ every few seconds."""
    u = request.user
    if getattr(u, "is_blocked", False) or not getattr(u, "is_email_verified", True):
        return Response({"detail": "Verify your email to use the article writer."}, status=403)
    topic = re.sub(r"\s+", " ", str(request.data.get("topic") or "")).strip()[:200]
    if len(topic) < 5:
        return Response({"detail": "Write a heading of at least a few words first."}, status=400)
    lang = str(request.data.get("lang") or "en")
    lang = lang if lang in LANGS else "en"
    words = LENGTHS.get(str(request.data.get("length") or "medium"), 1000)
    with_image = str(request.data.get("image", "1")).lower() not in ("0", "false", "no", "")
    per_user, site = _limits()
    if _used(u) + ARTICLE_COST > per_user:
        return Response({"detail": "You have used today's AI allowance. The article writer will be back for you tomorrow."}, status=429)
    if _site_used() + ARTICLE_COST > site:
        return Response({"detail": TOO_BUSY}, status=429)
    dk = "ai_art_day:%d:%s" % (u.pk, timezone.localdate())
    if (cache.get(dk) or 0) >= ARTICLE_DAY_MAX:
        return Response({"detail": "You can draft %d articles a day with AI. Try again tomorrow." % ARTICLE_DAY_MAX}, status=429)
    if not cache.add("ai_art_busy:%d" % u.pk, 1, 330):
        return Response({"detail": "Your last article is still being written. Please wait for it."}, status=429)
    try:
        cache.incr(dk)
    except ValueError:
        cache.set(dk, 1, 90000)
    job = _uuid.uuid4().hex
    key = "ai_art:%d:%s" % (u.pk, job)
    cache.set(key, {"state": "working"}, 3600)
    _thr.Thread(target=_article_job, args=(key, u.pk, topic, lang, words, with_image), daemon=True).start()
    return Response({"job": job, "left": max(0, ARTICLE_DAY_MAX - (cache.get(dk) or 1))})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def article_job(request, job):
    d = cache.get("ai_art:%d:%s" % (request.user.pk, re.sub(r"[^0-9a-f]", "", job)[:32]))
    if not d:
        return Response({"state": "error", "detail": "This draft has expired. Please start again."}, status=404)
    return Response(d)
