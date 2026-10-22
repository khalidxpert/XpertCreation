"""Group roles like Discord - /api/groupx/<group id>/roles/...
GET    roles/                  roles of the group + who has which role (any member)
POST   roles/                  {name, color, icon, hoist} make a role (admins)
POST   roles/<rid>/            edit a role (admins)      DELETE roles/<rid>/  remove it (admins)
POST   roles/<rid>/members/    {uid, on: true|false} give or take a role (admins)
POST   roles/order/            {ids: [...]} top to bottom (admins)
"""
import re

from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.models import ChatGroup, GroupMember

from .models import GroupRole, GroupRoleMember

MAX_ROLES = 25
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _ctx(gid, u):
    g = ChatGroup.objects.filter(pk=gid).first()
    me = GroupMember.objects.filter(group=g, user=u).first() if g else None
    if not me:
        return None, None, False
    boss = me.role == "admin" or g.created_by_id == u.id or u.is_superuser
    return g, me, boss


def _clean(d, r=None):
    name = " ".join(str(d.get("name", r.name if r else "") or "").split())[:30]
    if not name:
        return None, "Give the role a name."
    color = str(d.get("color", r.color if r else "#5865F2") or "#5865F2")
    if not HEX.match(color):
        return None, "Pick a colour."
    icon = str(d.get("icon", r.icon if r else "") or "").strip()[:8]
    if re.search(r"[<>&\"']", icon + name):
        return None, "Please don't use < > & or quotes."
    hoist = bool(d.get("hoist", r.hoist if r else True))
    return {"name": name, "color": color.lower(), "icon": icon, "hoist": hoist}, None


def _out(g, u, boss):
    rs = list(GroupRole.objects.filter(group=g))
    holders = {}
    for rid, uid in GroupRoleMember.objects.filter(role__group=g).values_list("role_id", "user_id"):
        holders.setdefault(str(uid), []).append(rid)
    order = {r.id: i for i, r in enumerate(rs)}
    for k in holders:
        holders[k].sort(key=lambda x: order.get(x, 99))
    return Response({"roles": [{"id": r.id, "name": r.name, "color": r.color, "icon": r.icon, "hoist": r.hoist, "count": sum(1 for v in holders.values() if r.id in v)} for r in rs],
                     "members": holders, "can_manage": boss})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def roles(request, gid):
    g, me, boss = _ctx(gid, request.user)
    if not g:
        return _err("Group not found.", 404)
    if request.method == "POST":
        if not boss:
            return _err("Only admins can make roles.", 403)
        if GroupRole.objects.filter(group=g).count() >= MAX_ROLES:
            return _err("A group can have up to %d roles." % MAX_ROLES)
        if not cache.add("xcrole:%d" % request.user.pk, 1, 1):
            return _err("Please wait a moment.", 429)
        data, er = _clean(request.data)
        if er:
            return _err(er)
        if GroupRole.objects.filter(group=g, name__iexact=data["name"]).exists():
            return _err("There is already a role with that name.")
        last = GroupRole.objects.filter(group=g).order_by("-position").first()
        GroupRole.objects.create(group=g, position=(last.position + 1) if last else 0, **data)
    return _out(g, request.user, boss)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def role(request, gid, rid):
    g, me, boss = _ctx(gid, request.user)
    if not g:
        return _err("Group not found.", 404)
    if not boss:
        return _err("Only admins can change roles.", 403)
    r = GroupRole.objects.filter(group=g, pk=rid).first()
    if not r:
        return _err("Role not found.", 404)
    if request.method == "DELETE":
        r.delete()
    else:
        data, er = _clean(request.data, r)
        if er:
            return _err(er)
        if GroupRole.objects.filter(group=g, name__iexact=data["name"]).exclude(pk=r.pk).exists():
            return _err("There is already a role with that name.")
        for k, v in data.items():
            setattr(r, k, v)
        r.save()
    return _out(g, request.user, boss)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def give(request, gid, rid):
    g, me, boss = _ctx(gid, request.user)
    if not g:
        return _err("Group not found.", 404)
    if not boss:
        return _err("Only admins can give roles.", 403)
    r = GroupRole.objects.filter(group=g, pk=rid).first()
    try:
        uid = int(request.data.get("uid"))
    except (TypeError, ValueError):
        return _err("Who?")
    if not r or not GroupMember.objects.filter(group=g, user_id=uid).exists():
        return _err("Not found.", 404)
    if request.data.get("on", True):
        GroupRoleMember.objects.get_or_create(role=r, user_id=uid)
        try:
            from notifications.views import notify
            from django.contrib.auth import get_user_model
            if uid != request.user.id:
                notify(get_user_model().objects.get(pk=uid), "group", "You got the role \"%s\" in %s" % (r.name, g.name), "/group/%d" % g.id)
        except Exception:
            pass
    else:
        GroupRoleMember.objects.filter(role=r, user_id=uid).delete()
    return _out(g, request.user, boss)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order(request, gid):
    g, me, boss = _ctx(gid, request.user)
    if not g:
        return _err("Group not found.", 404)
    if not boss:
        return _err("Only admins can change roles.", 403)
    ids = request.data.get("ids") or []
    mine = {r.id: r for r in GroupRole.objects.filter(group=g)}
    i = 0
    for x in ids:
        try:
            r = mine.get(int(x))
        except (TypeError, ValueError):
            continue
        if r:
            r.position = i; r.save(update_fields=["position"]); i += 1
    return _out(g, request.user, boss)
