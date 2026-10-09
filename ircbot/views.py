"""Endpoints for XpertBot (IRC). Only the bot can call them: header X-IRC-Bot-Secret must match IRC_BOT_SECRET in .env."""
import hmac
import json
import os
import re
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt


def _secret():
    m = re.search(r"^IRC_BOT_SECRET=(.*)$", open(os.path.join(settings.BASE_DIR, ".env")).read(), re.M)
    return m.group(1).strip().strip('"\'') if m else ""


def _ok(request):
    s = _secret()
    return bool(s) and hmac.compare_digest(s, request.headers.get("X-IRC-Bot-Secret", ""))


@csrf_exempt
def post(request):
    if request.method != "POST" or not _ok(request):
        return JsonResponse({"detail": "Not allowed."}, status=403)
    try:
        d = json.loads(request.body.decode() or "{}")
    except Exception:
        d = {}
    acct, text = str(d.get("account") or "").strip(), str(d.get("text") or "").strip()
    u = get_user_model().objects.filter(username__iexact=acct, is_active=True).first() if acct else None
    if not u:
        return JsonResponse({"detail": "No XpertCreation member with that name."}, status=404)
    if len(text) < 3 or len(text) > 2000:
        return JsonResponse({"detail": "Write 3 to 2000 characters."}, status=400)
    Post = apps.get_model("feed", "Post")
    if Post.objects.filter(author=u, created_at__gte=timezone.now() - timedelta(minutes=10)).count() >= 3:
        return JsonResponse({"detail": "Slow down: at most 3 posts in 10 minutes."}, status=429)
    p = Post.objects.create(author=u, body=text, visibility="members")
    return JsonResponse({"ok": True, "id": p.id})


@csrf_exempt
def feed(request):
    if not _ok(request):
        return JsonResponse({"detail": "Not allowed."}, status=403)
    now = timezone.now()
    Req = apps.get_model("bloodbank", "Request")
    Item = apps.get_model("donations", "DonationItem")
    blood = [{"id": r.id, "group": r.blood_group, "units": r.units, "city": r.city, "hospital": r.hospital, "urgency": r.urgency,
              "created": r.created_at.isoformat()}
             for r in Req.objects.filter(status="open", expires_at__gt=now).order_by("-id")[:40]]
    donate = [{"id": i.id, "title": i.title, "category": i.get_category_display() if hasattr(i, "get_category_display") else i.category,
               "condition": i.condition, "quantity": i.quantity, "city": i.city, "created": i.created_at.isoformat()}
              for i in Item.objects.filter(state="available").order_by("-id")[:40]]
    last_b = Req.objects.order_by("-id").values_list("id", flat=True).first() or 0
    last_d = Item.objects.order_by("-id").values_list("id", flat=True).first() or 0
    return JsonResponse({"blood": blood, "donate": donate, "blood_max": last_b, "donate_max": last_d})
