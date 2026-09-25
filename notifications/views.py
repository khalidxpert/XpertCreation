from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

import os
import secrets

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from .models import ChatBlock, ChatMessage, ChatReport, ChatThread, Notification

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
    try:
        from .push import send as _push
        _push(user, kind, text, link)
    except Exception:
        pass


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

CONTEXT_LABEL = {"donate": "", "blood": "Blood request", "connect": "Connection"}
MAX_PHOTO = 2 * 1024 * 1024
PHOTOS_PER_DAY = 20
TYPING_SECONDS = 6


def _name(u):
    return (getattr(u, "full_name", "") or "").strip() or "Member"


def _blocked(a, b):
    """True if either person has blocked the other."""
    return ChatBlock.objects.filter(Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)).exists()


def _url(path):
    return (settings.MEDIA_URL.rstrip("/") + "/" + path) if path else ""


def _msg(m, me):
    return {"id": m.id, "body": m.body, "image": _url(m.image), "mine": m.author_id == me.id,
            "read": m.read, "when": m.created_at.strftime("%d %b, %H:%M")}


def _save_photo(f, thread_id):
    from PIL import Image, ImageOps
    if not f:
        raise ValueError("Pick a photo.")
    if f.size > MAX_PHOTO:
        raise ValueError("That photo is over 2 MB.")
    try:
        im = Image.open(f)
        fmt = im.format
        im.load()
    except Exception:
        raise ValueError("That file is not a photo we can read.")
    if fmt not in ("JPEG", "PNG", "WEBP", "GIF"):
        raise ValueError("Use a JPG, PNG or WebP photo.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1280, 1280))
    rel = "chat/%d/%s.webp" % (thread_id, secrets.token_hex(12))
    full = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    try:
        im.save(full, "WEBP", quality=78, method=4)
    except Exception:                                   # Pillow without WebP: fall back to JPEG
        rel = rel[:-5] + ".jpg"
        full = os.path.join(settings.MEDIA_ROOT, rel)
        im.save(full, "JPEG", quality=80, optimize=True)
    return rel


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
            "with": _name(other),
            "about": titles.get(t.ref_id, "") if t.context == "donate" else CONTEXT_LABEL.get(t.context, ""),
            "last": (("\U0001F3F7 Sticker" if last.body.startswith("[sticker:") else last.body[:80]) or ("\U0001F4F7 Photo" if last.image else "")) if last else "",
            "unread": unread,
            "updated": t.updated_at.strftime("%d %b, %H:%M"),
        })
    return Response({"threads": out})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """Unread messages across all chats - for the badge in the menu. Cached for ten seconds."""
    key = "chat_unread:%d" % request.user.pk
    n = cache.get(key)
    if n is None:
        n = ChatMessage.objects.filter(Q(thread__a=request.user) | Q(thread__b=request.user), read=False) \
                               .exclude(author=request.user).count()
        cache.set(key, n, 10)
    return Response({"unread": n})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@throttle_classes([ChatThrottle])
def thread_detail(request, pk):
    t = ChatThread.objects.filter(id=pk).first()
    if not t or not t.has(request.user):
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    other = t.other(request.user)

    if request.method == "GET":
        if t.messages.exclude(author=request.user).filter(read=False).update(read=True):
            cache.delete("chat_unread:%d" % request.user.pk)
        try:
            after = int(request.GET.get("after") or 0)
        except ValueError:
            after = 0
        qs = t.messages.all()
        if after:
            qs = qs.filter(id__gt=after)
        # the newest of my messages the other person has read - so ticks can turn blue
        seen = t.messages.filter(author=request.user, read=True).order_by("-id").values_list("id", flat=True).first() or 0
        return Response({
            "id": t.id, "context": t.context, "ref_id": t.ref_id, "with": _name(other),
            "messages": [_msg(m, request.user) for m in qs],
            "seen_upto": seen,
            "typing": bool(cache.get("chat_typing:%d:%d" % (t.id, other.id))),
            "blocked": _blocked(request.user, other),
            "i_blocked": ChatBlock.objects.filter(blocker=request.user, blocked=other).exists(),
        })

    if _blocked(request.user, other):
        return _err("You cannot send messages in this chat.", status.HTTP_403_FORBIDDEN)
    body = str(request.data.get("message") or "").strip()[:2000]
    photo = request.FILES.get("photo")
    rel = ""
    if photo:
        today = timezone.localdate()
        sent = ChatMessage.objects.filter(author=request.user, created_at__date=today).exclude(image="").count()
        if sent >= PHOTOS_PER_DAY:
            return _err("You have sent %d photos today. Try again tomorrow." % PHOTOS_PER_DAY)
        try:
            rel = _save_photo(photo, t.id)
        except ValueError as e:
            return _err(str(e))
    if not body and not rel:
        return _err("Write something first.")
    m = ChatMessage.objects.create(thread=t, author=request.user, body=body, image=rel)
    t.save(update_fields=[])   # bumps updated_at via auto_now
    cache.delete("chat_typing:%d:%d" % (t.id, request.user.id))
    cache.delete("chat_unread:%d" % other.pk)
    notify(other, "chat_message", _name(request.user) + " sent you a message.", "/chat/" + str(t.id))
    return Response({"detail": "Sent.", "message": _msg(m, request.user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def thread_typing(request, pk):
    t = ChatThread.objects.filter(id=pk).first()
    if t and t.has(request.user):
        cache.set("chat_typing:%d:%d" % (t.id, request.user.id), 1, TYPING_SECONDS)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def thread_block(request, pk):
    """Block or unblock the other person in this chat. Blocking stops both sides from sending."""
    t = ChatThread.objects.filter(id=pk).first()
    if not t or not t.has(request.user):
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    other = t.other(request.user)
    old = ChatBlock.objects.filter(blocker=request.user, blocked=other).first()
    if old:
        old.delete()
        return Response({"i_blocked": False, "blocked": _blocked(request.user, other)})
    ChatBlock.objects.get_or_create(blocker=request.user, blocked=other)
    return Response({"i_blocked": True, "blocked": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def thread_report(request, pk):
    t = ChatThread.objects.filter(id=pk).first()
    if not t or not t.has(request.user):
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    reason = request.data.get("reason")
    if reason not in dict(ChatReport.REASONS):
        return _err("Pick a reason.")
    ChatReport.objects.create(thread=t, reporter=request.user, reason=reason,
                              note=str(request.data.get("note") or "").strip()[:500])
    notify_admins("chat_report", "Chat reported (%s) by %s" % (reason, _name(request.user)), "/admin/notifications/chatreport/")
    return Response({"ok": True})


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
