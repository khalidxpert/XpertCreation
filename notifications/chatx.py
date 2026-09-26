"""Chat extras: sending documents, the media / links / docs tabs, contact details, and emailing a chat
to yourself. Documents are kept outside the public web folder and are only handed out, as downloads,
to the two people in the chat."""
import os
import re
import secrets
import threading

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.http import FileResponse
from django.utils import timezone
from django.utils.html import escape
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ChatMessage, ChatThread

FILES_DIR = getattr(settings, "CHAT_FILES_DIR", "/var/lib/gunicorn-academy/chat_files")
MAX_FILE = 5 * 1024 * 1024
FILES_PER_DAY = 20
EXPORTS_PER_DAY = 3
ATTACH_LIMIT = 15 * 1024 * 1024
OK_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv"}
LINK = re.compile(r"https?://[^\s<>\"']+")


def _looks_right(ext, head):
    if ext == "pdf":
        return head.startswith(b"%PDF")
    if ext in ("docx", "xlsx", "pptx"):
        return head.startswith(b"PK\x03\x04")
    if ext in ("doc", "xls", "ppt"):
        return head.startswith(b"\xD0\xCF\x11\xE0")
    try:
        head.decode("utf-8")
        return b"\x00" not in head
    except UnicodeDecodeError:
        return False


def save_file(f, thread_id):
    """Check and store a document. Returns (stored path, original name, size)."""
    name = os.path.basename(str(f.name or "file"))[:120]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in OK_EXT:
        raise ValueError("You can send PDF, Word, Excel, PowerPoint, text and CSV files.")
    if f.size > MAX_FILE:
        raise ValueError("That file is over 5 MB.")
    head = f.read(4096)
    f.seek(0)
    if not _looks_right(ext, head):
        raise ValueError("That file does not look like a real .%s file." % ext)
    rel = "%d/%s.%s" % (thread_id, secrets.token_hex(12), ext)
    full = os.path.join(FILES_DIR, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)
    return rel, name, f.size


def _thread(pk, user):
    t = ChatThread.objects.filter(id=pk).first()
    return t if t and t.has(user) else None


def contact(u):
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).first()
    except Exception:
        p = None
    return {"slug": p.slug if p else None, "headline": p.headline if p else "",
            "city": getattr(p, "city", "") if p else ""}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def file_download(request, pk):
    m = ChatMessage.objects.select_related("thread").filter(id=pk).exclude(attachment="").first()
    if not m or not m.thread.has(request.user):
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    path = os.path.join(FILES_DIR, m.attachment)
    if not os.path.exists(path):
        return Response({"detail": "This file is no longer available."}, status=status.HTTP_404_NOT_FOUND)
    r = FileResponse(open(path, "rb"), as_attachment=True, filename=m.attachment_name, content_type="application/octet-stream")
    r["X-Content-Type-Options"] = "nosniff"
    return r


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def thread_media(request, pk):
    from .views import _visible, _url
    t = _thread(pk, request.user)
    if not t:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    media, links, docs = [], [], []
    for m in _visible(t, request.user).order_by("-id")[:1000]:
        when = m.created_at.strftime("%d %b %Y")
        if m.image:
            media.append({"id": m.id, "url": _url(m.image), "when": when})
        if m.attachment:
            docs.append({"id": m.id, "name": m.attachment_name, "size": m.attachment_size, "url": "/api/notify/files/%d/" % m.id, "when": when})
        for l in LINK.findall(m.body or ""):
            links.append({"url": l.rstrip(".,)"), "when": when, "mine": m.author_id == request.user.id})
    return Response({"media": media, "links": links, "docs": docs})


def _send_export(user, t, rows, attachments, other_name):
    lines = ["%s  %s: %s" % (w, n, x) for w, n, x in rows]
    text = "Your chat with %s on XpertCreation (%d messages).\n\n%s\n\n-- XpertCreation" % (other_name, len(rows), "\n".join(lines))
    body = "".join("<tr><td style='color:#667;white-space:nowrap;padding:3px 8px 3px 0;vertical-align:top'>%s</td><td style='padding:3px 8px 3px 0;vertical-align:top'><b>%s</b></td><td style='padding:3px 0'>%s</td></tr>"
                   % (escape(w), escape(n), escape(x).replace("\n", "<br>")) for w, n, x in rows)
    html = ("<p>Your chat with <b>%s</b> on XpertCreation (%d messages).</p><table style='font:14px Arial,sans-serif;border-collapse:collapse'>%s</table>"
            "<p style='color:#667;font-size:12px'>You asked for this copy from the chat menu. Keep it private: it contains both sides of the conversation.</p>"
            % (escape(other_name), len(rows), body))
    msg = EmailMultiAlternatives("Your chat with %s" % other_name, text, getattr(settings, "DEFAULT_FROM_EMAIL", None), [user.email])
    msg.attach_alternative(html, "text/html")
    import mimetypes
    for name, path in attachments:
        try:
            with open(path, "rb") as fh:
                msg.attach(name, fh.read(), mimetypes.guess_type(name)[0] or "application/octet-stream")
        except Exception:
            pass
    try:
        msg.send(fail_silently=True)
    except Exception:
        pass


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def thread_export(request, pk):
    """body: { media: true | false }. Emails the chat to the signed-in member's own address only."""
    from .views import _name, _visible
    t = _thread(pk, request.user)
    if not t:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    if not getattr(request.user, "email", ""):
        return Response({"detail": "Your account has no email address."}, status=400)
    key = "chat_export:%d:%s" % (request.user.pk, timezone.localdate())
    n = cache.get(key, 0)
    if n >= EXPORTS_PER_DAY:
        return Response({"detail": "You can email chats %d times a day. Try again tomorrow." % EXPORTS_PER_DAY}, status=429)
    cache.set(key, n + 1, 90000)
    with_media = str(request.data.get("media", False)).lower() in ("true", "1")
    other = t.other(request.user)
    rows, atts, total, skipped = [], [], 0, 0
    for m in _visible(t, request.user).select_related("author").order_by("id"):
        who = _name(m.author)
        txt = m.body or ""
        if txt.startswith("[sticker:"):
            txt = "[sticker]"
        if m.image:
            path = os.path.join(settings.MEDIA_ROOT, m.image)
            if with_media and os.path.exists(path) and total + os.path.getsize(path) <= ATTACH_LIMIT:
                nm = "photo-%d%s" % (m.id, os.path.splitext(path)[1])
                atts.append((nm, path)); total += os.path.getsize(path)
                txt = (txt + " " if txt else "") + "[photo attached: %s]" % nm
            else:
                skipped += with_media
                txt = (txt + " " if txt else "") + "[photo]"
        if m.attachment:
            path = os.path.join(FILES_DIR, m.attachment)
            if with_media and os.path.exists(path) and total + os.path.getsize(path) <= ATTACH_LIMIT:
                atts.append((m.attachment_name, path)); total += os.path.getsize(path)
                txt = (txt + " " if txt else "") + "[file attached: %s]" % m.attachment_name
            else:
                skipped += with_media
                txt = (txt + " " if txt else "") + "[file: %s]" % m.attachment_name
        rows.append((timezone.localtime(m.created_at).strftime("%d %b %Y %H:%M"), who, txt))
    if not rows:
        return Response({"detail": "There are no messages to send."}, status=400)
    threading.Thread(target=_send_export, args=(request.user, t, rows, atts, _name(other)), daemon=True).start()
    email = request.user.email
    shown = email[:2] + "***" + email[email.find("@"):] if "@" in email else "your email"
    return Response({"ok": True, "to": shown, "messages": len(rows), "attached": len(atts), "too_big": skipped})
