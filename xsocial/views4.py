"""/api/xsocial/msg/ - edit and delete one-to-one chat messages.
msg/<id>/edit/    POST {body}          your own text message, within 24 hours; shows "edited"
msg/<id>/delete/  POST {everyone}      everyone=true: your own message, removed for both ("This message was deleted");
                                       otherwise: hidden only for you
msg/states/?ids=  GET                  edits / deletes on these messages (the chat page checks every few seconds)"""
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MsgHide, MsgState
from .views import _err, _ids

EDIT_HOURS = 24


def _mine(request, mid):
    from notifications.models import ChatMessage
    m = ChatMessage.objects.filter(pk=mid).select_related("thread").first()
    if not m or not m.thread.has(request.user):
        return None
    return m


def _rm(path, base):
    if not path:
        return
    try:
        full = os.path.realpath(os.path.join(str(base), path))
        if full.startswith(os.path.realpath(str(base)) + os.sep) and os.path.isfile(full):
            os.remove(full)
    except OSError:
        pass


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def msg_edit(request, mid):
    m = _mine(request, mid)
    if not m:
        return _err("Message not found.", 404)
    if m.author_id != request.user.pk or m.system:
        return _err("You can edit only your own messages.", 403)
    if m.created_at < timezone.now() - timedelta(hours=EDIT_HOURS):
        return _err("Messages can be edited for %d hours after sending." % EDIT_HOURS)
    st = MsgState.objects.filter(message=m).first()
    if st and st.deleted_at:
        return _err("This message was deleted.")
    body = str(request.data.get("body") or "").strip()[:2000]
    if not body:
        return _err("Write something, or delete the message instead.")
    if body.startswith("[sticker:"):
        return _err("Stickers can't be edited.")
    if body != m.body:
        type(m).objects.filter(pk=m.pk).update(body=body)
        MsgState.objects.update_or_create(message=m, defaults={"edited_at": timezone.now()})
    return Response({"id": m.id, "body": body, "edited": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def msg_delete(request, mid):
    m = _mine(request, mid)
    if not m:
        return _err("Message not found.", 404)
    everyone = str(request.data.get("everyone")).lower() in ("true", "1")
    if not everyone:
        MsgHide.objects.get_or_create(message=m, user=request.user)
        return Response({"id": m.id, "hidden": True})
    if m.author_id != request.user.pk or m.system:
        return _err("You can delete only your own messages for everyone.", 403)
    try:
        from notifications.chatx import FILES_DIR
    except Exception:
        FILES_DIR = getattr(settings, "CHAT_FILES_DIR", "/var/lib/gunicorn-academy/chat_files")
    _rm(m.image, settings.MEDIA_ROOT); _rm(m.attachment, FILES_DIR); _rm(m.voice, FILES_DIR)
    type(m).objects.filter(pk=m.pk).update(body="", image="", voice="", voice_secs=0, attachment="", attachment_name="", attachment_size=0, pinned=False)
    MsgState.objects.update_or_create(message=m, defaults={"deleted_at": timezone.now()})
    return Response({"id": m.id, "deleted": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def msg_states(request):
    from notifications.models import ChatMessage
    u = request.user
    ids = _ids(request.GET.get("ids"), 200)
    ok = ChatMessage.objects.filter(pk__in=ids).select_related("thread")
    allowed = {m.pk: m for m in ok if m.thread.has(u)}
    out = {}
    for st in MsgState.objects.filter(message_id__in=list(allowed)):
        m = allowed[st.message_id]
        out[st.message_id] = {"deleted": bool(st.deleted_at), "edited": bool(st.edited_at), "body": "" if st.deleted_at else m.body}
    for mid in MsgHide.objects.filter(user=u, message_id__in=list(allowed)).values_list("message_id", flat=True):
        out.setdefault(mid, {})["hidden"] = True
    return Response({"states": out})
