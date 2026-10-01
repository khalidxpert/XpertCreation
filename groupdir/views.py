"""Groups directory: groups and channels whose admins chose to list them, with rankings and top creators."""
import secrets
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Listing


def _f(model, *names):
    have = {f.name for f in model._meta.fields}
    return next((n for n in names if n in have), None)


def _ensure_code(g):
    if not g.invite_code:
        g.invite_code = secrets.token_urlsafe(9)[:12]
        g.save(update_fields=["invite_code"])


def on_create(g, data):
    """Called by group creation: list it if the creator ticked 'show in the directory'."""
    if str(data.get("listed")).lower() in ("1", "true", "yes", "on"):
        _ensure_code(g)
        Listing.objects.create(group=g, listed=True)


def _creator(u):
    try:
        from accounts.views import avatar_url
        av = avatar_url(u.avatar)
    except Exception:
        av = ""
    return {"name": (getattr(u, "full_name", "") or getattr(u, "username", "") or "Member").strip(), "username": getattr(u, "username", "") or "", "avatar_url": av}


@api_view(["GET"])
@permission_classes([AllowAny])
def directory(request):
    """?sort=members|active|growing|new  ?q=  - listed groups and channels."""
    from notifications.groups import _url
    from notifications.models import ChatGroup, GroupMember, GroupMessage
    week = timezone.now() - timedelta(days=7)
    mt, jt = _f(GroupMessage, "created_at", "sent_at"), _f(GroupMember, "joined_at", "created_at")
    qs = ChatGroup.objects.filter(listing__listed=True).select_related("created_by").annotate(n=Count("members", distinct=True))
    if mt:
        qs = qs.annotate(act=Count("messages", filter=Q(**{"messages__" + mt + "__gte": week}), distinct=True))
    if jt:
        qs = qs.annotate(grow=Count("members", filter=Q(**{"members__" + jt + "__gte": week}), distinct=True))
    q = str(request.GET.get("q") or "").strip()[:60]
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    sort = request.GET.get("sort") or "members"
    order = {"members": ["-n", "-id"], "active": ["-act", "-n"] if mt else ["-n"], "growing": ["-grow", "-n"] if jt else ["-n"], "new": ["-created_at"]}.get(sort, ["-n"])
    out = []
    for i, g in enumerate(qs.order_by(*order)[:60]):
        if not g.invite_code:
            continue
        out.append({"rank": i + 1, "id": g.id, "name": g.name, "photo": _url(g.photo), "purpose": g.description, "channel": g.only_admins_send,
                    "members": g.n, "active_week": getattr(g, "act", 0), "new_members_week": getattr(g, "grow", 0),
                    "created": timezone.localtime(g.created_at).strftime("%d %b %Y"), "creator": _creator(g.created_by) if g.created_by_id else None,
                    "join": "/group/join/" + g.invite_code})
    return Response({"groups": out, "sort": sort})


@api_view(["GET"])
@permission_classes([AllowAny])
def creators(request):
    """Top creators: members across the listed groups they created."""
    from django.contrib.auth import get_user_model
    from notifications.models import ChatGroup
    rows = (ChatGroup.objects.filter(listing__listed=True, created_by__isnull=False).values("created_by")
            .annotate(groups=Count("id", distinct=True), members=Count("members", distinct=True)).order_by("-members")[:30])
    users = {u.pk: u for u in get_user_model().objects.filter(pk__in=[r["created_by"] for r in rows])}
    return Response({"creators": [dict(_creator(users[r["created_by"]]), rank=i + 1, groups=r["groups"], members=r["members"])
                                  for i, r in enumerate(rows) if r["created_by"] in users]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def mine(request):
    """GET: groups you admin, with their directory state. POST {group, listed}: switch it (admins only)."""
    from notifications.models import ChatGroup, GroupMember
    if request.method == "POST":
        try:
            gid = int(request.data.get("group"))
        except (TypeError, ValueError):
            return Response({"detail": "Choose a group."}, status=400)
        if not GroupMember.objects.filter(group_id=gid, user=request.user, role="admin").exists():
            return Response({"detail": "Only the group's admins can change this."}, status=403)
        g = ChatGroup.objects.get(pk=gid)
        on = str(request.data.get("listed")).lower() in ("1", "true", "yes", "on")
        if on: _ensure_code(g)
        Listing.objects.update_or_create(group=g, defaults={"listed": on})
    gids = GroupMember.objects.filter(user=request.user, role="admin").values_list("group_id", flat=True)
    out = [{"id": g.id, "name": g.name, "channel": g.only_admins_send, "listed": bool(getattr(g, "listing", None) and g.listing.listed),
            "has_link": bool(g.invite_code)} for g in ChatGroup.objects.filter(pk__in=list(gids)).select_related("listing").order_by("name")]
    return Response({"groups": out})
