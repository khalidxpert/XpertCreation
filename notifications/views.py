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

CONTEXT_LABEL = {"donate": "", "blood": "Blood request", "connect": "Connection", "job": "Job application"}
MAX_PHOTO = 2 * 1024 * 1024
PHOTOS_PER_DAY = 20
TYPING_SECONDS = 6


def _name(u):
    return (getattr(u, "full_name", "") or "").strip() or "Member"


def _avatar(u):
    try:
        from network.views import _av
        return _av(u) or ""
    except Exception:
        return ""


def _blocked(a, b):
    """True if either person has blocked the other."""
    return ChatBlock.objects.filter(Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)).exists()


def _url(path):
    return (settings.MEDIA_URL.rstrip("/") + "/" + path) if path else ""


def _msg(m, me):
    return {"id": m.id, "body": m.body, "image": _url(m.image), "mine": m.author_id == me.id,
            "read": m.read, "system": m.system, "file": ({"name": m.attachment_name, "size": m.attachment_size, "url": "/api/notify/files/%d/" % m.id} if m.attachment else None), "when": m.created_at.strftime("%d %b, %H:%M")}


DISAPPEAR = {0: "Off", 24: "24 hours", 168: "7 days", 2160: "90 days"}


def _side(t, user):
    return "a" if user.id == t.a_id else "b"


def _cleared(t, user):
    return getattr(t, _side(t, user) + "_cleared_at")


def _visible(t, user):
    """The messages this person can still see: after they cleared the chat, and not expired."""
    qs = t.messages.all()
    c = _cleared(t, user)
    if c:
        qs = qs.filter(created_at__gt=c)
    if t.disappear_hours:
        qs = qs.filter(created_at__gt=timezone.now() - timezone.timedelta(hours=t.disappear_hours))
    return qs


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
        if getattr(t, _side(t, request.user) + "_hidden"):
            continue
        other = t.other(request.user)
        vis = _visible(t, request.user)
        unread = vis.filter(read=False).exclude(author=request.user).count()
        last = vis.last()
        out.append({
            "id": t.id, "context": t.context, "ref_id": t.ref_id,
            "with": _name(other), "avatar": _avatar(other),
            "about": titles.get(t.ref_id, "") if t.context == "donate" else CONTEXT_LABEL.get(t.context, ""),
            "last": (("\U0001F3F7 Sticker" if last.body.startswith("[sticker:") else last.body[:80]) or ("\U0001F4F7 Photo" if last.image else "") or (("\U0001F4C4 " + last.attachment_name) if last.attachment else "")) if last else "",
            "unread": unread, "disappear": t.disappear_hours,
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
        try:
            from .groups import unread_for
            n += unread_for(request.user)
        except Exception:
            pass
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
        qs = _visible(t, request.user)
        if after:
            qs = qs.filter(id__gt=after)
        # the newest of my messages the other person has read - so ticks can turn blue
        seen = t.messages.filter(author=request.user, read=True).order_by("-id").values_list("id", flat=True).first() or 0
        return Response({
            "id": t.id, "context": t.context, "ref_id": t.ref_id, "with": _name(other), "avatar": _avatar(other),
            "messages": [_msg(m, request.user) for m in qs],
            "seen_upto": seen,
            "typing": bool(cache.get("chat_typing:%d:%d" % (t.id, other.id))),
            "blocked": _blocked(request.user, other),
            "i_blocked": ChatBlock.objects.filter(blocker=request.user, blocked=other).exists(),
            "disappear": t.disappear_hours,
            "contact": __import__("notifications.chatx", fromlist=["contact"]).contact(other),
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
    att = None
    if request.FILES.get("file"):
        from .chatx import FILES_PER_DAY, save_file
        if ChatMessage.objects.filter(author=request.user, created_at__date=timezone.localdate()).exclude(attachment="").count() >= FILES_PER_DAY:
            return _err("You have sent %d files today. Try again tomorrow." % FILES_PER_DAY)
        try:
            att = save_file(request.FILES["file"], t.id)
        except ValueError as e:
            return _err(str(e))
    if not body and not rel and not att:
        return _err("Write something first.")
    m = ChatMessage.objects.create(thread=t, author=request.user, body=body, image=rel,
                                   attachment=att[0] if att else "", attachment_name=att[1] if att else "", attachment_size=att[2] if att else 0)
    t.a_hidden = t.b_hidden = False
    t.save(update_fields=["a_hidden", "b_hidden", "updated_at"])
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


def _clear_for(t, user, hide):
    side = _side(t, user)
    setattr(t, side + "_cleared_at", timezone.now())
    fields = [side + "_cleared_at"]
    if hide:
        setattr(t, side + "_hidden", True)
        fields.append(side + "_hidden")
    t.save(update_fields=fields)
    t.messages.exclude(author=user).filter(read=False).update(read=True)
    cache.delete("chat_unread:%d" % user.pk)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def thread_clear(request, pk):
    """Clear the messages for me only (the other person keeps theirs). With {"delete": true} the chat
    also leaves my list until someone writes again - like deleting a chat on WhatsApp."""
    t = ChatThread.objects.filter(id=pk).first()
    if not t or not t.has(request.user):
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    _clear_for(t, request.user, bool(request.data.get("delete")))
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def threads_delete(request):
    """body: { ids: [3, 7] } - delete several chats from my list at once."""
    ids = request.data.get("ids") or []
    if not isinstance(ids, list):
        return _err("Pick some chats.")
    done = 0
    for t in ChatThread.objects.filter(id__in=[int(i) for i in ids[:100] if str(i).isdigit()]):
        if t.has(request.user):
            _clear_for(t, request.user, True)
            done += 1
    return Response({"deleted": done})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def thread_disappear(request, pk):
    """body: { hours: 0 | 24 | 168 | 2160 }. Applies to the whole chat, for both people, as on WhatsApp.
    A line in the chat tells both of them who changed it."""
    t = ChatThread.objects.filter(id=pk).first()
    if not t or not t.has(request.user):
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    try:
        hours = int(request.data.get("hours"))
    except (TypeError, ValueError):
        hours = -1
    if hours not in DISAPPEAR:
        return _err("Pick 24 hours, 7 days, 90 days or off.")
    if hours != t.disappear_hours:
        t.disappear_hours = hours
        t.save(update_fields=["disappear_hours"])
        text = (_name(request.user) + " turned on disappearing messages: new and old messages leave this chat after " + DISAPPEAR[hours] + "."
                if hours else _name(request.user) + " turned off disappearing messages.")
        ChatMessage.objects.create(thread=t, author=request.user, body=text, system=True)
    return Response({"disappear": t.disappear_hours})


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
