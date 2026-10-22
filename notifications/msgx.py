"""Message actions for XpertChat (setup_xpertchat_v3) - /api/notify/...
forward/                                POST {src: "t"|"g", mid, to: [["t", id], ["g", id], ...]}  forward to up to 5 chats / groups
groups/<pk>/messages/<mid>/delete/      POST  delete a group message for everyone (your own, or any if you are an admin)
groups/<pk>/messages/<mid>/private/     POST  reply privately: opens the one-to-one chat with the writer (once you are connected)
stickers/pack/                          GET   my stickers as a ZIP, sized for WhatsApp (via a sticker app), Telegram and Discord
Also: @mentions in groups notify the people named (and @all, admins only), and "[re:..]" / "[fwd]" markers are
hidden in chat list previews and phone notifications."""
import io
import os
import re
import zipfile

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import groups as G, views as V
from .models import ChatMessage, ChatThread, GroupMember, GroupMessage, ChatGroup

MARK = re.compile(r"^\s*(?:\[re:\d+\]|\[fwd\])\s*")
ALL_FOR_EVERYONE = False          # @all: admins only. Set True to let every member use it.


def clean(t):
    t = t or ""
    while MARK.match(t):
        t = MARK.sub("", t, count=1)
    return t


def _err(m, c=400):
    return Response({"detail": m}, status=c)


# ---------------------------------------------------------------- forward
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def forward(request):
    u, d = request.user, request.data
    if not cache.add("xcfwd:%d" % u.pk, 1, 3):
        return _err("Slow down a little.", 429)
    try:
        mid = int(d.get("mid"))
    except (TypeError, ValueError):
        return _err("Message not found.", 404)
    if d.get("src") == "g":
        m = GroupMessage.objects.select_related("group").filter(pk=mid, hidden=False).first()
        if not m or not G._me(m.group, u):
            return _err("Message not found.", 404)
    else:
        m = ChatMessage.objects.select_related("thread").filter(pk=mid).first()
        if not m or not m.thread.has(u):
            return _err("Message not found.", 404)
    body = clean(m.body)
    if body.startswith("[sticker:"):
        fbody = body
    else:
        fbody = ("[fwd] " + body).strip()
    targets = d.get("to") or []
    if not isinstance(targets, list) or not targets:
        return _err("Choose where to send it.")
    sent, problems = 0, []
    for kind, tid in targets[:5]:
        try:
            tid = int(tid)
        except (TypeError, ValueError):
            continue
        if kind == "t":
            t = ChatThread.objects.filter(pk=tid).first()
            if not t or not t.has(u):
                problems.append("a chat was not found"); continue
            other = t.other(u)
            if V._blocked(u, other):
                problems.append("you can't message %s" % V._name(other)); continue
            ChatMessage.objects.create(thread=t, author=u, body=fbody, image=m.image, voice=m.voice, voice_secs=m.voice_secs,
                                       attachment=m.attachment, attachment_name=m.attachment_name, attachment_size=m.attachment_size)
            t.a_hidden = t.b_hidden = False
            t.save(update_fields=["a_hidden", "b_hidden", "updated_at"])
            cache.delete("chat_unread:%d" % other.pk)
            V.notify(other, "chat_message", V._name(u) + " sent you a message.", "/chat/" + str(t.id))
            sent += 1
        elif kind == "g":
            g = ChatGroup.objects.filter(pk=tid).first()
            me = G._me(g, u) if g else None
            if not me:
                problems.append("a group was not found"); continue
            if g.only_admins_send and me.role != "admin":
                problems.append("only admins can post in %s" % g.name); continue
            try:
                from .groupbot import check
                stop = check(g, me, fbody)
            except Exception:
                stop = None
            if stop:
                problems.append("%s: %s" % (g.name, stop)); continue
            GroupMessage.objects.create(group=g, author=u, body=fbody, image=m.image, voice=m.voice, voice_secs=m.voice_secs,
                                        attachment=m.attachment, attachment_name=m.attachment_name, attachment_size=m.attachment_size)
            g.save(update_fields=["updated_at"])
            G._push(g, u, clean(fbody) or "Forwarded a message")
            sent += 1
    if not sent:
        return _err("Not sent: " + "; ".join(problems) if problems else "Not sent.")
    return Response({"sent": sent, "problems": problems})


# ---------------------------------------------------------------- groups: delete for everyone, reply privately
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_delete(request, pk, mid):
    u = request.user
    g = ChatGroup.objects.filter(pk=pk).first()
    me = G._me(g, u) if g else None
    m = GroupMessage.objects.filter(pk=mid, group_id=pk, hidden=False).first() if me else None
    if not m:
        return _err("Message not found.", 404)
    if m.author_id != u.id and me.role != "admin":
        return _err("You can delete your own messages. Admins can delete any message.", 403)
    m.hidden, m.pinned = True, False
    m.save(update_fields=["hidden", "pinned"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_private(request, pk, mid):
    u = request.user
    g = ChatGroup.objects.filter(pk=pk).first()
    me = G._me(g, u) if g else None
    m = GroupMessage.objects.select_related("author").filter(pk=mid, group_id=pk).first() if me else None
    if not m or not m.author_id or m.bot:
        return _err("Message not found.", 404)
    if m.author_id == u.id:
        return _err("That is your own message.")
    other = m.author
    try:
        from network.models import Connection
        from network.views import _between
        c = _between(u, other)
        connected = bool(c and c.state == Connection.ACCEPTED)
    except Exception:
        c, connected = None, False
    slug = ""
    try:
        from network.models import ProProfile
        slug = ProProfile.objects.filter(user=other).values_list("slug", flat=True).first() or ""
    except Exception:
        pass
    if not connected:
        return Response({"connect": True, "slug": slug, "name": V._name(other)})
    t = V.open_thread("connect", c.pk, u, other)
    return Response({"thread": t.id, "name": V._name(other)})


# ---------------------------------------------------------------- @mentions in groups
def _mentions(g, sender, body):
    body = clean(body)
    if "@" not in body:
        return
    me = G._me(g, sender)
    low = body.lower()
    members = list(GroupMember.objects.filter(group=g).exclude(user=sender).select_related("user"))
    everyone = re.search(r"(^|\s)@(all|everyone)\b", low) and (ALL_FOR_EVERYONE or (me and me.role == "admin"))
    short = clean(body)[:70]
    for gm in members:
        nm = (V._name(gm.user) or "").strip()
        hit = everyone or (nm and ("@" + nm.lower()) in low) or (nm and ("@" + nm.split(" ")[0].lower() + " ") in (low + " ") and sum(1 for x in members if (V._name(x.user) or "").split(" ")[0].lower() == nm.split(" ")[0].lower()) == 1)
        if hit:
            V.notify(gm.user, "chat_message", "%s mentioned %s in %s: %s" % (V._name(sender), "everyone" if everyone else "you", g.name, short), "/group/%d" % g.id)


def _wrap_group_detail():
    orig = G.group_detail
    if getattr(orig, "_xcm", False):
        return

    def view(request, pk):
        resp = orig(request, pk)
        try:
            if request.method == "POST" and getattr(resp, "status_code", 500) == 200:
                body = str(((getattr(resp, "data", None) or {}).get("message") or {}).get("body") or "")
                if "@" in body:
                    g = ChatGroup.objects.filter(pk=pk).first()
                    if g:
                        _mentions(g, request.user, body)
        except Exception:
            pass
        return resp
    view._xcm = True
    view.csrf_exempt = getattr(orig, "csrf_exempt", False)
    G.group_detail = view


def _wrap_push():                 # phone notifications without the reply / forward markers
    orig = G._push
    if getattr(orig, "_xcm", False):
        return

    def push(g, sender, text):
        return orig(g, sender, clean(text) or "Message")
    push._xcm = True
    G._push = push


_wrap_group_detail()
_wrap_push()


# ---------------------------------------------------------------- sticker pack download
README = """XpertChat sticker pack
======================

WhatsApp  (folder: whatsapp)
  WhatsApp does not let websites add sticker packs, so use a free sticker app:
  Android / iPhone: install "Sticker Maker" (or any "personal stickers for WhatsApp" app), make a new pack,
  add the pictures from the whatsapp folder (3 to 30 stickers), then tap "Add to WhatsApp".
  tray.png is the pack icon. Animated stickers are in whatsapp/animated (keep them in their own pack).

Telegram  (folder: telegram)
  Open Telegram, message @Stickers, send /newpack, then send each PNG as a file with an emoji.

Discord  (folder: discord)
  Server Settings -> Stickers -> Upload Sticker. Choose a file from the discord folder (320 x 320, under 512 KB).

Made with XpertChat - https://xpertcreation.com/chat
"""


def _fit(im, size):
    from PIL import Image
    im = im.convert("RGBA"); im.thumbnail((size, size))
    c = Image.new("RGBA", (size, size), (0, 0, 0, 0)); c.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return c


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sticker_pack(request):
    from PIL import Image, ImageSequence
    from .stickers import _dir, _list
    u = request.user
    items = _list(u)
    if not items:
        return _err("You have no stickers yet. Make one first.", 404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", README)
        tray = None
        for i, s in enumerate(items[:30], 1):
            p = os.path.join(_dir(u), s["name"])
            try:
                im = Image.open(p)
            except Exception:
                continue
            if s["anim"] and getattr(im, "is_animated", False):
                fr, du = [], []
                for f in ImageSequence.Iterator(im):
                    fr.append(_fit(f, 512)); du.append(max(40, int(f.info.get("duration", 80) or 80)))
                for q in (55, 40, 28):
                    b = io.BytesIO(); fr[0].save(b, "WEBP", save_all=True, append_images=fr[1:], duration=du, loop=0, quality=q, method=4)
                    if b.tell() <= 500 * 1024:
                        break
                z.writestr("whatsapp/animated/sticker_%02d.webp" % i, b.getvalue())
                small = [_fit(f, 320) for f in fr[::2]]
                b = io.BytesIO(); small[0].save(b, "PNG", save_all=True, append_images=small[1:], duration=[d * 2 for d in du[::2]], loop=0, optimize=True)
                if b.tell() <= 512 * 1024:
                    z.writestr("discord/sticker_%02d.png" % i, b.getvalue())
                first = fr[0]
            else:
                first = _fit(im, 512)
                for q in (80, 60, 40):
                    b = io.BytesIO(); first.save(b, "WEBP", quality=q, method=4)
                    if b.tell() <= 100 * 1024:
                        break
                z.writestr("whatsapp/sticker_%02d.webp" % i, b.getvalue())
                b = io.BytesIO(); first.save(b, "PNG", optimize=True); z.writestr("telegram/sticker_%02d.png" % i, b.getvalue())
                b = io.BytesIO(); _fit(im, 320).save(b, "PNG", optimize=True); z.writestr("discord/sticker_%02d.png" % i, b.getvalue())
            if tray is None:
                tray = first.copy(); tray.thumbnail((96, 96)); t = Image.new("RGBA", (96, 96), (0, 0, 0, 0)); t.paste(tray, ((96 - tray.width) // 2, (96 - tray.height) // 2), tray)
                b = io.BytesIO(); t.save(b, "PNG"); z.writestr("whatsapp/tray.png", b.getvalue())
    r = HttpResponse(buf.getvalue(), content_type="application/zip")
    r["Content-Disposition"] = 'attachment; filename="xpertchat-stickers-%s.zip"' % timezone.localdate().isoformat()
    return r
