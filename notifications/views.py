from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import ChatMessage, ChatThread, Notification

User = get_user_model()


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


class ChatThrottle(SimpleRateThrottle):
    scope = "chat"
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def notify(user, kind, text, link=""):
    """
    The one place anything in the project creates a bell entry. Other apps
    import this rather than writing to the Notification table directly, so
    the shape of a notification only has to be right in one place.
    """
    if not user or not user.is_authenticated:
        return
    Notification.objects.create(user=user, kind=kind, text=text[:200], link=link[:200])


def notify_admins(kind, text, link=""):
    """For events every admin should see - a new donation post, say."""
    for admin in User.objects.filter(is_superuser=True):
        notify(admin, kind, text, link)


def open_thread(context, ref_id, user_a, user_b):
    """Get or create the thread between these two people about this item.
    Order-independent: (a, b) and (b, a) are the same conversation."""
    t = ChatThread.objects.filter(context=context, ref_id=ref_id) \
                          .filter(a=user_a, b=user_b).first() \
        or ChatThread.objects.filter(context=context, ref_id=ref_id) \
                          .filter(a=user_b, b=user_a).first()
    if t:
        return t
    return ChatThread.objects.create(context=context, ref_id=ref_id, a=user_a, b=user_b)


# ---------------------------------------------------------------- bell

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_notifications(request):
    rows = Notification.objects.filter(user=request.user)[:40]
    unread = Notification.objects.filter(user=request.user, read=False).count()
    return Response({"unread": unread, "notifications": [{
        "id": n.id, "kind": n.kind, "text": n.text, "link": n.link,
        "read": n.read, "when": n.created_at.strftime("%d %b, %H:%M"),
    } for n in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request):
    """body: { id: 5 } for one, or {} for all."""
    nid = request.data.get("id")
    qs = Notification.objects.filter(user=request.user, read=False)
    if nid:
        qs = qs.filter(id=nid)
    n = qs.update(read=True)
    return Response({"marked": n})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clear_all(request):
    """Deletes every notification for this account - read or not. A
    separate action from marking read, since clearing is not reversible
    the way un-reading is not offered either, but the person should still
    be able to empty the list rather than just silence it."""
    n = Notification.objects.filter(user=request.user).delete()[0]
    return Response({"cleared": n})


# ---------------------------------------------------------------- chat

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_threads(request):
    rows = (ChatThread.objects.filter(a=request.user) | ChatThread.objects.filter(b=request.user)) \
           .distinct().order_by("-updated_at")[:40]
    out = []

    # What each conversation is about. Two people can have several threads -
    # one per item - and without this they all read as the same name twice.
    titles = {}
    donate_ids = [t.ref_id for t in rows if t.context == "donate"]
    if donate_ids:
        try:
            from donations.models import DonationItem
            titles = dict(DonationItem.objects.filter(id__in=donate_ids)
                          .values_list("id", "title"))
        except Exception:
            titles = {}

    for t in rows:
        other = t.other(request.user)
        unread = t.messages.filter(read=False).exclude(author=request.user).count()
        last = t.messages.last()
        out.append({
            "id": t.id, "context": t.context, "ref_id": t.ref_id,
            "with": (other.full_name or "").strip() or other.email.split("@")[0],
            "about": titles.get(t.ref_id, "") if t.context == "donate" else "Blood request",
            "last": last.body[:80] if last else "",
            "unread": unread,
            "updated": t.updated_at.strftime("%d %b, %H:%M"),
        })
    return Response({"threads": out})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def thread_detail(request, pk):
    t = ChatThread.objects.filter(id=pk).first()
    if not t or not t.has(request.user):
        return _err("Not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        t.messages.exclude(author=request.user).update(read=True)
        other = t.other(request.user)
        return Response({
            "id": t.id, "context": t.context, "ref_id": t.ref_id,
            "with": (other.full_name or "").strip() or other.email.split("@")[0],
            "messages": [{
                "body": m.body, "mine": m.author_id == request.user.id,
                "when": m.created_at.strftime("%d %b, %H:%M"),
            } for m in t.messages.all()],
        })

    body = str(request.data.get("message") or "").strip()
    if len(body) < 1:
        return _err("Write something first.")
    ChatMessage.objects.create(thread=t, author=request.user, body=body[:2000])
    t.save(update_fields=[])   # bumps updated_at via auto_now

    other = t.other(request.user)
    who = (request.user.full_name or "").strip() or request.user.email.split("@")[0]
    notify(other, "chat_message", who + " sent you a message.",
          "/chat/" + str(t.id))

    return Response({"detail": "Sent."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_thread(request):
    """body: { context: "donate"|"blood", ref_id: 5, with_user: 12 }
    Only usable once the two people are already connected - accepting a
    donation request, or a blood ask. This does not let a stranger open a
    chat with someone who has not agreed to anything."""
    context = request.data.get("context")
    if context not in ("donate", "blood"):
        return _err("Unknown context.")
    try:
        ref_id = int(request.data.get("ref_id"))
        other_id = int(request.data.get("with_user"))
    except (TypeError, ValueError):
        return _err("Missing information.")

    other = User.objects.filter(id=other_id).first()
    if not other or other.id == request.user.id:
        return _err("Cannot start that chat.")

    t = open_thread(context, ref_id, request.user, other)
    return Response({"id": t.id})
