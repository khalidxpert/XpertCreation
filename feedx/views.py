"""Connect extras: people suggestions for @mentions and tags, feeling / check-in / tagged people on a post,
and /u/<username> links."""
import re

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import PostMeta

U = get_user_model()
FEELINGS = {"happy": "\U0001F60A happy", "loved": "\U0001F970 loved", "blessed": "\U0001F64F blessed", "excited": "\U0001F929 excited",
            "grateful": "\U0001F917 grateful", "proud": "\U0001F60E proud", "motivated": "\U0001F4AA motivated", "relaxed": "\U0001F60C relaxed",
            "celebrating": "\U0001F389 celebrating", "travelling": "\u2708\uFE0F travelling", "working": "\U0001F4BC working", "studying": "\U0001F4DA studying",
            "eating": "\U0001F37D\uFE0F eating", "watching": "\U0001F3AC watching", "sad": "\U0001F622 sad", "tired": "\U0001F634 tired"}
MAX_TAGS = 10
BACKGROUNDS = {"blue", "sunset", "green", "night", "pink", "gold", "sky", "red", "purple", "black", "cream", "white"}
TEXT_COLOURS = {"white", "black", "yellow", "blue"}


def _person(u):
    try:
        from accounts.views import avatar_url
        av = avatar_url(u.avatar)
    except Exception:
        av = ""
    return {"id": u.pk, "name": (getattr(u, "full_name", "") or u.username or "Member").strip(), "username": u.username or "", "avatar_url": av}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def people(request):
    """?q= : members with a username, your connections first."""
    q = str(request.GET.get("q") or "").strip().lstrip("@")[:40]
    qs = U.objects.filter(is_active=True, is_blocked=False, username__isnull=False).exclude(pk=request.user.pk)
    if q:
        qs = qs.filter(Q(username__istartswith=q) | Q(full_name__icontains=q))
    try:
        from feed.views import _connected_ids
        conn = set(_connected_ids(request.user))
    except Exception:
        conn = set()
    rows = list(qs.order_by("full_name")[:60])
    rows.sort(key=lambda u: (u.pk not in conn, (u.full_name or "").lower()))
    return Response({"people": [dict(_person(u), connected=u.pk in conn) for u in rows[:8]]})


def _meta_out(m):
    people = {u.pk: u for u in U.objects.filter(pk__in=m.tagged or [])}
    return {"feeling": FEELINGS.get(m.feeling, ""), "feeling_key": m.feeling, "place": m.place,
            "tagged": [_person(people[i]) for i in (m.tagged or []) if i in people], "bg": m.bg, "fg": m.fg}


@api_view(["GET"])
@permission_classes([AllowAny])
def meta(request):
    """?ids=1,2,3 : feeling, place and tagged people for posts you can see."""
    from feed.models import Post
    from feed.views import _can_see
    ids = [int(x) for x in re.findall(r"\d+", str(request.GET.get("ids") or ""))[:60]]
    out = {}
    for m in PostMeta.objects.filter(post_id__in=ids).select_related("post"):
        if _can_see(m.post, request.user):
            out[m.post_id] = _meta_out(m)
    return Response({"meta": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_meta(request, pk):
    """{feeling, place, tagged:[ids]} on your own post. Newly tagged people get a notification if they can see it."""
    from feed.models import Post
    from feed.views import _can_see
    from network.views import _name
    from notifications.views import notify
    p = Post.objects.filter(pk=pk, author=request.user).first()
    if not p:
        return Response({"detail": "Post not found."}, status=404)
    feeling = str(request.data.get("feeling") or "")
    feeling = feeling if feeling in FEELINGS else ""
    place = re.sub(r"\s+", " ", str(request.data.get("place") or "")).strip()[:120]
    want = []
    for x in (request.data.get("tagged") or [])[:MAX_TAGS]:
        try:
            want.append(int(x))
        except (TypeError, ValueError):
            pass
    tagged = list(U.objects.filter(pk__in=want, is_active=True).exclude(pk=request.user.pk).values_list("pk", flat=True))
    bg = str(request.data.get("bg") or "")
    bg = bg if bg in BACKGROUNDS and not p.images and len(p.body or "") <= 300 else ""
    fg = str(request.data.get("fg") or "")
    fg = (fg if fg in TEXT_COLOURS else ("black" if bg in ("cream", "white", "gold") else "white")) if bg else ""
    m, _ = PostMeta.objects.get_or_create(post=p)
    before = set(m.tagged or [])
    m.feeling, m.place, m.tagged, m.bg, m.fg = feeling, place, tagged, bg, fg
    m.save()
    for u in U.objects.filter(pk__in=[i for i in tagged if i not in before]):
        try:
            if _can_see(p, u):
                notify(u, "tag", "%s tagged you in a post." % _name(request.user), "/post/%d" % p.id)
        except Exception:
            pass
    return Response({"meta": _meta_out(m)})


@api_view(["GET"])
@permission_classes([AllowAny])
def feelings(request):
    return Response({"feelings": [{"key": k, "label": v} for k, v in FEELINGS.items()]})


def by_username(request, username):
    """/u/<username>: that member's Connect profile if they have one, otherwise their posts."""
    u = U.objects.filter(username__iexact=username, is_active=True).first()
    if not u:
        return HttpResponseRedirect("/feed")
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).first()
        if p and p.slug:
            return HttpResponseRedirect("/in/" + p.slug)
    except Exception:
        pass
    return HttpResponseRedirect("/feed?user=%d" % u.pk)
