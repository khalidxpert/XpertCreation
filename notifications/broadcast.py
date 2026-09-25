"""Broadcast: the super admin and staff send one message to every member - in the bell, and on phones
that turned notifications on. Five broadcasts a day at most, so a slip of the finger cannot spam everyone."""
import threading

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import Broadcast, Notification

User = get_user_model()
PER_DAY = 5


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.is_staff))


def _people(audience):
    qs = User.objects.filter(is_active=True)
    if any(f.name == "is_blocked" for f in User._meta.get_fields()):
        qs = qs.filter(is_blocked=False)
    if audience == "verified" and any(f.name == "is_email_verified" for f in User._meta.get_fields()):
        qs = qs.filter(is_email_verified=True)
    return qs


def _devices(user_ids):
    try:
        from .models import PushSubscription
        return list(PushSubscription.objects.filter(user_id__in=user_ids).values_list("id", flat=True))
    except Exception:
        return []


def _name(u):
    return (getattr(u, "full_name", "") or "").strip() or getattr(u, "email", "") or "Admin"


@api_view(["GET", "POST"])
@permission_classes([IsAdmin])
def broadcast(request):
    if request.method == "GET":
        return Response({"counts": {"all": _people("all").count(), "verified": _people("verified").count()},
                         "history": [{"id": b.id, "text": b.text, "link": b.link, "audience": b.audience, "push": b.push,
                                      "recipients": b.recipients, "devices": b.devices, "by": _name(b.sent_by) if b.sent_by else "",
                                      "when": timezone.localtime(b.created_at).strftime("%d %b %Y, %H:%M")}
                                     for b in Broadcast.objects.select_related("sent_by")[:30]]})
    d = request.data
    text = str(d.get("text") or "").strip()[:200]
    if len(text) < 5:
        return Response({"detail": "Write the message (at least a few words)."}, status=400)
    link = str(d.get("link") or "").strip()[:200]
    if link and not (link.startswith("/") or link.startswith("https://")):
        return Response({"detail": "The link must start with / (a page on this site) or https://"}, status=400)
    audience = d.get("audience") if d.get("audience") in dict(Broadcast.AUDIENCE) else "all"
    push = str(d.get("push", True)).lower() not in ("false", "0", "")
    if Broadcast.objects.filter(created_at__date=timezone.localdate()).count() >= PER_DAY:
        return Response({"detail": "Five broadcasts have gone out today already. Try again tomorrow."}, status=429)
    ids = list(_people(audience).values_list("id", flat=True))
    now = timezone.now()
    Notification.objects.bulk_create([Notification(user_id=i, kind="broadcast", text=text, link=link, created_at=now) for i in ids], batch_size=1000)
    devices = _devices(ids) if push else []
    b = Broadcast.objects.create(sent_by=request.user, text=text, link=link, audience=audience, push=push,
                                 recipients=len(ids), devices=len(devices))
    if devices:
        try:
            from .push import _deliver, _payload
            data = _payload("broadcast", text, link or "/")
            threading.Thread(target=_deliver, args=(devices, data), daemon=True).start()
        except Exception:
            pass
    return Response({"id": b.id, "recipients": len(ids), "devices": len(devices)}, status=201)
