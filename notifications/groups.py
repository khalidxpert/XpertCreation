"""Group chats. Members add people from their connections; each member decides who may add them
straight away (everyone / connections / nobody) - anyone else sends an invitation to accept or decline.
Admins manage members, settings and an invite link."""
import os
import re
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ChatGroup, GroupInvite, GroupMember, GroupMessage, GroupPrivacy

User = get_user_model()
MAX_MEMBERS = 256
GROUPS_PER_DAY = 5
PHOTOS_PER_DAY = 20


def _err(msg, code=400):
    return Response({"detail": msg}, status=code)


def _name(u):
    return ((getattr(u, "full_name", "") or "").strip() or "Member") if u else "Someone"


def _avatar(u):
    try:
        from network.views import _av
        return _av(u) or ""
    except Exception:
        return ""


def _url(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p else ""


def _connected(a, b):
    try:
        from network.models import Connection
        return Connection.objects.filter(Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a), state=Connection.ACCEPTED).exists()
    except Exception:
        return False


def _may_add(adder, person):
    who = GroupPrivacy.objects.filter(user=person).values_list("who", flat=True).first() or "connections"
    return who == "everyone" or (who == "connections" and _connected(adder, person))


def _me(g, u):
    return GroupMember.objects.filter(group=g, user=u).first()


def _say(g, text):
    GroupMessage.objects.create(group=g, body=text, system=True)
    g.save(update_fields=["updated_at"])


def _push(g, sender, text):
    """Phones of members who have not muted the group - no bell entries, like WhatsApp."""
    try:
        from .push import send
    except Exception:
        return
    for m in GroupMember.objects.filter(group=g, muted=False).exclude(user=sender).select_related("user")[:MAX_MEMBERS]:
        send(m.user, "chat_message", "%s in %s: %s" % (_name(sender), g.name, text[:80]), "/group/%d" % g.id)
    cache.delete_many(["chat_unread:%d" % uid for uid in GroupMember.objects.filter(group=g).values_list("user_id", flat=True)])


def _save_photo(f, prefix):
    from PIL import Image, ImageOps
    if f.size > 2 * 1024 * 1024:
        raise ValueError("That photo is over 2 MB.")
    try:
        im = Image.open(f); fmt = im.format; im.load()
    except Exception:
        raise ValueError("That file is not a photo we can read.")
    if fmt not in ("JPEG", "PNG", "WEBP", "GIF"):
        raise ValueError("Use a JPG, PNG or WebP photo.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1280, 1280))
    rel = "chat/%s/%s.webp" % (prefix, secrets.token_hex(12))
    full = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=78)
    return rel


def unread_for(user):
    n = 0
    for m in GroupMember.objects.filter(user=user, muted=False).values("group_id", "last_read_id"):
        n += GroupMessage.objects.filter(group_id=m["group_id"], id__gt=m["last_read_id"]).exclude(author=user).count()
    return n


def _add_people(g, adder, ids):
    added, invited, skipped = [], [], 0
    count = GroupMember.objects.filter(group=g).count()
    for uid in ids[:100]:
        p = User.objects.filter(id=uid, is_active=True).first()
        if not p or p == adder or GroupMember.objects.filter(group=g, user=p).exists():
            skipped += 1; continue
        if count >= MAX_MEMBERS:
            break
        try:
            from .models import ChatBlock
            if ChatBlock.objects.filter(Q(blocker=p, blocked=adder) | Q(blocker=adder, blocked=p)).exists():
                skipped += 1; continue
        except Exception:
            pass
        if _may_add(adder, p):
            GroupMember.objects.create(group=g, user=p); count += 1; added.append(_name(p))
            try:
                from .views import notify
                notify(p, "chat_message", "%s added you to the group %s." % (_name(adder), g.name), "/group/%d" % g.id)
            except Exception:
                pass
        else:
            inv, made = GroupInvite.objects.get_or_create(group=g, user=p, defaults={"invited_by": adder})
            if not made and inv.status != "pending":
                inv.status, inv.invited_by = "pending", adder; inv.save(update_fields=["status", "invited_by"])
            invited.append(_name(p))
            try:
                from .views import notify
                notify(p, "chat_message", "%s invited you to join the group %s." % (_name(adder), g.name), "/chat?invites=1")
            except Exception:
                pass
    if added:
        _say(g, "%s added %s" % (_name(adder), ", ".join(added[:10]) + (" and %d more" % (len(added) - 10) if len(added) > 10 else "")))
    return added, invited, skipped


def _info(g, u):
    me = _me(g, u)
    members = [{"id": m.user_id, "name": _name(m.user), "avatar": _avatar(m.user), "role": m.role, "me": m.user_id == u.id}
               for m in GroupMember.objects.filter(group=g).select_related("user").order_by("role", "joined_at")]
    return {"id": g.id, "name": g.name, "description": g.description, "photo": _url(g.photo),
            "only_admins_send": g.only_admins_send, "only_admins_edit": g.only_admins_edit,
            "invite_link": ("/group/join/" + g.invite_code) if (g.invite_code and me and me.role == "admin") else "",
            "my_role": me.role if me else None, "muted": me.muted if me else False, "members": members}


def _msg(m, u):
    return {"id": m.id, "body": m.body, "image": _url(m.image), "system": m.system, "mine": m.author_id == u.id,
            "author": _name(m.author) if m.author_id else "", "author_id": m.author_id, "avatar": _avatar(m.author) if m.author_id else "",
            "file": ({"name": m.attachment_name, "size": m.attachment_size, "url": "/api/notify/groups/files/%d/" % m.id} if m.attachment else None),
            "when": m.created_at.strftime("%d %b, %H:%M")}


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def groups(request):
    u = request.user
    if request.method == "GET":
        out = []
        for m in GroupMember.objects.filter(user=u).select_related("group").order_by("-group__updated_at")[:100]:
            g = m.group
            last = GroupMessage.objects.filter(group=g).order_by("-id").first()
            unread = GroupMessage.objects.filter(group=g, id__gt=m.last_read_id).exclude(author=u).count()
            txt = ""
            if last:
                txt = (last.body[:60] if not last.body.startswith("[sticker:") else "\U0001F3F7 Sticker") or ("\U0001F4F7 Photo" if last.image else ("\U0001F4C4 " + last.attachment_name if last.attachment else ""))
                if last.author_id and not last.system:
                    txt = ("You" if last.author_id == u.id else _name(last.author).split(" ")[0]) + ": " + txt
            out.append({"id": g.id, "name": g.name, "photo": _url(g.photo), "last": txt, "unread": unread, "muted": m.muted,
                        "updated": g.updated_at.strftime("%d %b, %H:%M")})
        return Response({"groups": out, "invites": GroupInvite.objects.filter(user=u, status="pending").count()})
    d = request.data
    name = str(d.get("name") or "").strip()[:80]
    if len(name) < 2:
        return _err("Give the group a name.")
    if ChatGroup.objects.filter(created_by=u, created_at__date=timezone.localdate()).count() >= GROUPS_PER_DAY:
        return _err("You can create %d groups a day." % GROUPS_PER_DAY, 429)
    g = ChatGroup.objects.create(name=name, description=str(d.get("description") or "").strip()[:300], created_by=u)
    GroupMember.objects.create(group=g, user=u, role="admin")
    _say(g, "%s created the group" % _name(u))
    ids = [int(i) for i in (d.get("members") or []) if str(i).isdigit()]
    added, invited, _ = _add_people(g, u, ids)
    return Response({"id": g.id, "added": len(added), "invited": len(invited)}, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def group_detail(request, pk):
    u = request.user
    g = ChatGroup.objects.filter(id=pk).first()
    me = _me(g, u) if g else None
    if not g or not me:
        return _err("You are not in this group.", 404)
    if request.method == "GET":
        try:
            after = int(request.GET.get("after") or 0)
        except ValueError:
            after = 0
        qs = GroupMessage.objects.filter(group=g, created_at__gte=me.joined_at).select_related("author")   # from when you joined, like WhatsApp
        if after:
            qs = qs.filter(id__gt=after)
        msgs = list(qs.order_by("-id")[:300])[::-1]
        top = GroupMessage.objects.filter(group=g).order_by("-id").values_list("id", flat=True).first() or 0
        if top > me.last_read_id:
            GroupMember.objects.filter(pk=me.pk).update(last_read_id=top); cache.delete("chat_unread:%d" % u.pk)
        typing = [n for uid, n in (cache.get("grp_typing:%d" % g.id) or {}).items() if int(uid) != u.id]
        out = {"messages": [_msg(m, u) for m in msgs], "typing": typing[:3]}
        if not after:
            out["group"] = _info(g, u)
        return Response(out)
    if g.only_admins_send and me.role != "admin":
        return _err("Only admins can send messages in this group.", 403)
    if not cache.add("grp_busy:%d" % u.pk, 1, 1):
        return _err("Slow down a little.", 429)
    body = str(request.data.get("message") or "").strip()[:2000]
    rel, att = "", None
    if request.FILES.get("photo"):
        if GroupMessage.objects.filter(author=u, created_at__date=timezone.localdate()).exclude(image="").count() >= PHOTOS_PER_DAY:
            return _err("You have sent %d photos today." % PHOTOS_PER_DAY)
        try:
            rel = _save_photo(request.FILES["photo"], "g%d" % g.id)
        except ValueError as e:
            return _err(str(e))
    if request.FILES.get("file"):
        from .chatx import save_file
        try:
            att = save_file(request.FILES["file"], 1000000000 + g.id)
        except ValueError as e:
            return _err(str(e))
    if not body and not rel and not att:
        return _err("Write something first.")
    m = GroupMessage.objects.create(group=g, author=u, body=body, image=rel, attachment=att[0] if att else "",
                                    attachment_name=att[1] if att else "", attachment_size=att[2] if att else 0)
    g.save(update_fields=["updated_at"])
    GroupMember.objects.filter(pk=me.pk).update(last_read_id=m.id)
    typ = cache.get("grp_typing:%d" % g.id) or {}
    typ.pop(str(u.id), None); cache.set("grp_typing:%d" % g.id, typ, 8)
    _push(g, u, body or ("Photo" if rel else "File"))
    return Response({"message": _msg(m, u)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_typing(request, pk):
    if GroupMember.objects.filter(group_id=pk, user=request.user).exists():
        key = "grp_typing:%d" % pk
        typ = cache.get(key) or {}
        typ[str(request.user.id)] = _name(request.user).split(" ")[0]
        cache.set(key, typ, 6)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def group_settings(request, pk):
    """Name, description, photo and the two admin switches."""
    u = request.user
    g = ChatGroup.objects.filter(id=pk).first()
    me = _me(g, u) if g else None
    if not me:
        return _err("You are not in this group.", 404)
    d = request.data
    if (g.only_admins_edit or "only_admins_send" in d or "only_admins_edit" in d) and me.role != "admin":
        return _err("Only admins can change this.", 403)
    changed = []
    if d.get("name") and str(d["name"]).strip()[:80] != g.name:
        g.name = str(d["name"]).strip()[:80]; changed.append("the name to \u201c%s\u201d" % g.name)
    if "description" in d:
        g.description = str(d.get("description") or "").strip()[:300]; changed.append("the description")
    for k in ("only_admins_send", "only_admins_edit"):
        if k in d:
            setattr(g, k, str(d.get(k)).lower() in ("true", "1"))
    if request.FILES.get("photo"):
        try:
            g.photo = _save_photo(request.FILES["photo"], "g%d" % g.id); changed.append("the group photo")
        except ValueError as e:
            return _err(str(e))
    g.save()
    if changed:
        _say(g, "%s changed %s" % (_name(u), " and ".join(changed)))
    if "only_admins_send" in d:
        _say(g, "%s set the group so %s can send messages" % (_name(u), "only admins" if g.only_admins_send else "everyone"))
    return Response(_info(g, u))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_members(request, pk):
    """body: { add: [user ids] } - admins only."""
    g = ChatGroup.objects.filter(id=pk).first()
    me = _me(g, request.user) if g else None
    if not me or me.role != "admin":
        return _err("Only admins can add people.", 403)
    ids = [int(i) for i in (request.data.get("add") or []) if str(i).isdigit()]
    added, invited, skipped = _add_people(g, request.user, ids)
    return Response({"added": added, "invited": invited, "skipped": skipped, "group": _info(g, request.user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_member(request, pk, uid):
    """body: { action: remove | make_admin | dismiss_admin } - admins only."""
    g = ChatGroup.objects.filter(id=pk).first()
    me = _me(g, request.user) if g else None
    m = GroupMember.objects.filter(group=g, user_id=uid).select_related("user").first() if g else None
    if not me or me.role != "admin" or not m or m.user_id == request.user.id:
        return _err("Not allowed.", 403)
    a = request.data.get("action")
    if a == "remove":
        m.delete(); _say(g, "%s removed %s" % (_name(request.user), _name(m.user)))
    elif a in ("make_admin", "dismiss_admin"):
        m.role = "admin" if a == "make_admin" else "member"; m.save(update_fields=["role"])
        if a == "make_admin":
            _say(g, "%s is now an admin" % _name(m.user))
    else:
        return _err("Unknown action.")
    return Response(_info(g, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_leave(request, pk):
    g = ChatGroup.objects.filter(id=pk).first()
    me = _me(g, request.user) if g else None
    if not me:
        return _err("You are not in this group.", 404)
    was_admin = me.role == "admin"
    me.delete()
    rest = GroupMember.objects.filter(group=g).order_by("joined_at")
    if not rest.exists():
        g.delete(); return Response({"left": True, "deleted": True})
    _say(g, "%s left" % _name(request.user))
    if was_admin and not rest.filter(role="admin").exists():
        first = rest.first(); first.role = "admin"; first.save(update_fields=["role"])
        _say(g, "%s is now an admin" % _name(first.user))
    return Response({"left": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_mute(request, pk):
    me = GroupMember.objects.filter(group_id=pk, user=request.user).first()
    if not me:
        return _err("You are not in this group.", 404)
    me.muted = not me.muted; me.save(update_fields=["muted"]); cache.delete("chat_unread:%d" % request.user.pk)
    return Response({"muted": me.muted})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_report(request, pk):
    g = ChatGroup.objects.filter(id=pk).first()
    if not g or not _me(g, request.user):
        return _err("Not found.", 404)
    from .views import notify_admins
    notify_admins("chat_report", "Group reported (%s) by %s: %s" % (str(request.data.get("reason") or "other")[:20], _name(request.user), g.name), "/admin/notifications/chatgroup/%d/change/" % g.id)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_link(request, pk):
    """body: { action: get | reset | off } - admins only."""
    g = ChatGroup.objects.filter(id=pk).first()
    me = _me(g, request.user) if g else None
    if not me or me.role != "admin":
        return _err("Only admins can manage the invite link.", 403)
    a = request.data.get("action") or "get"
    if a == "off":
        g.invite_code = ""
    elif a == "reset" or not g.invite_code:
        g.invite_code = secrets.token_urlsafe(9)[:12]
    g.save(update_fields=["invite_code"])
    return Response({"link": ("/group/join/" + g.invite_code) if g.invite_code else ""})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def group_join(request, code):
    g = ChatGroup.objects.filter(invite_code=code).exclude(invite_code="").first() if re.match(r"^[\w-]{6,16}$", code or "") else None
    if not g:
        return _err("This invite link is not valid any more.", 404)
    if request.method == "GET":
        return Response({"id": g.id, "name": g.name, "description": g.description, "photo": _url(g.photo),
                         "members": GroupMember.objects.filter(group=g).count(), "member": bool(_me(g, request.user))})
    if not _me(g, request.user):
        if GroupMember.objects.filter(group=g).count() >= MAX_MEMBERS:
            return _err("This group is full.")
        GroupMember.objects.create(group=g, user=request.user)
        _say(g, "%s joined using the invite link" % _name(request.user))
    return Response({"id": g.id})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invites(request):
    rows = GroupInvite.objects.filter(user=request.user, status="pending").select_related("group", "invited_by")
    return Response({"invites": [{"id": i.id, "group": i.group.name, "group_id": i.group_id, "photo": _url(i.group.photo),
                                  "by": _name(i.invited_by), "members": i.group.members.count()} for i in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_answer(request, pk, action):
    i = GroupInvite.objects.filter(id=pk, user=request.user, status="pending").select_related("group").first()
    if not i or action not in ("accept", "decline"):
        return _err("Not found.", 404)
    i.status = "accepted" if action == "accept" else "declined"
    i.save(update_fields=["status"])
    if action == "accept" and not _me(i.group, request.user):
        GroupMember.objects.create(group=i.group, user=request.user)
        _say(i.group, "%s joined" % _name(request.user))
    return Response({"status": i.status, "group_id": i.group_id})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def privacy(request):
    p, _ = GroupPrivacy.objects.get_or_create(user=request.user)
    if request.method == "POST" and request.data.get("who") in dict(GroupPrivacy.CHOICES):
        p.who = request.data["who"]; p.save(update_fields=["who"])
    return Response({"who": p.who})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def group_file(request, pk):
    from django.http import FileResponse
    from .chatx import FILES_DIR
    m = GroupMessage.objects.filter(id=pk).exclude(attachment="").first()
    if not m or not _me(m.group, request.user):
        return _err("Not found.", 404)
    path = os.path.join(FILES_DIR, m.attachment)
    if not os.path.exists(path):
        return _err("This file is no longer available.", 404)
    r = FileResponse(open(path, "rb"), as_attachment=True, filename=m.attachment_name, content_type="application/octet-stream")
    r["X-Content-Type-Options"] = "nosniff"
    return r
