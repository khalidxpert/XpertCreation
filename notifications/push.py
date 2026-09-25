"""Web push: phone and desktop notifications for everything that reaches the bell.

notify() in views.py calls send() after it writes the bell entry, so chat messages,
connection requests, endorsements, pet reminders and the rest all reach the phone.
Keys: VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY and VAPID_SUBJECT in the environment or .env.
"""
import json
import os
import threading

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import PushSubscription

TITLES = {"chat_message": "New message", "connect": "Connect", "endorse": "Endorsement", "follow": "New follower",
          "pet": "Your pet", "tick": "Blue tick", "report": "Report", "chat_report": "Chat report"}


def _env(name):
    v = getattr(settings, name, "") or os.environ.get(name, "")
    if v:
        return v
    base = getattr(settings, "BASE_DIR", "")
    try:
        with open(os.path.join(str(base), ".env")) as f:
            for line in f:
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _payload(kind, text, link):
    tag = "xc-" + (link or kind)
    return json.dumps({"title": TITLES.get(kind, "XpertCreation"), "body": text[:180],
                       "url": link or "/", "tag": tag})


def _deliver(sub_ids, data):
    from pywebpush import WebPushException, webpush
    key, subject = _env("VAPID_PRIVATE_KEY"), _env("VAPID_SUBJECT") or "mailto:admin@example.com"
    if not key:
        return
    for s in PushSubscription.objects.filter(id__in=sub_ids):
        try:
            webpush(subscription_info={"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}},
                    data=data, vapid_private_key=key, vapid_claims={"sub": subject}, ttl=86400, timeout=6)
            PushSubscription.objects.filter(id=s.id).update(last_ok=timezone.now(), fails=0)
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", 0)
            if code in (404, 410):                      # the phone unsubscribed or the address expired
                s.delete()
            else:
                PushSubscription.objects.filter(id=s.id).update(fails=s.fails + 1)
        except Exception:
            PushSubscription.objects.filter(id=s.id).update(fails=s.fails + 1)
    PushSubscription.objects.filter(fails__gte=20).delete()


def send(user, kind, text, link=""):
    """Queue a push for every device of this user. Never slows down or breaks the request."""
    try:
        ids = list(PushSubscription.objects.filter(user=user).values_list("id", flat=True))
        if ids and _env("VAPID_PRIVATE_KEY"):
            threading.Thread(target=_deliver, args=(ids, _payload(kind, text, link)), daemon=True).start()
    except Exception:
        pass


@api_view(["GET"])
@permission_classes([AllowAny])
def public_key(request):
    return Response({"key": _env("VAPID_PUBLIC_KEY")})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe(request):
    d = request.data or {}
    endpoint = str(d.get("endpoint") or "")[:600]
    keys = d.get("keys") or {}
    if not endpoint.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
        return Response({"detail": "That subscription is not complete."}, status=400)
    if PushSubscription.objects.filter(user=request.user).count() >= 10:
        PushSubscription.objects.filter(user=request.user).order_by("created_at").first().delete()
    PushSubscription.objects.update_or_create(endpoint=endpoint, defaults={
        "user": request.user, "p256dh": str(keys["p256dh"])[:200], "auth": str(keys["auth"])[:100], "fails": 0})
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unsubscribe(request):
    PushSubscription.objects.filter(user=request.user, endpoint=str(request.data.get("endpoint") or "")[:600]).delete()
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def test(request):
    send(request.user, "test", "Notifications are working. You will hear about new messages here.", "/chat")
    return Response({"ok": True, "devices": PushSubscription.objects.filter(user=request.user).count()})
