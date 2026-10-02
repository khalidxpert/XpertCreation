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

from .models import CommentReaction, PostMeta

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
    try:
        from prefs.views import hide_from_search
        qs = hide_from_search(qs, request.user, None)
    except ImportError:
        pass
    rows = list(qs.order_by("full_name")[:60])
    rows.sort(key=lambda u: (u.pk not in conn, (u.full_name or "").lower()))
    people = [dict(_person(u), connected=u.pk in conn) for u in rows[:8]]
    if request.GET.get("with") == "companies":
        people = _companies(q) + people
    return Response({"people": people[:8]})


def _companies(q):
    """Company pages for @ suggestions: @-name is the page name with _ instead of -."""
    try:
        from companies.models import Company
        from companies.views import _media
    except Exception:
        return []
    qs = Company.objects.filter(hidden=False).filter(Q(domain_verified_at__isnull=False) | Q(status=Company.APPROVED))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(slug__istartswith=q.replace("_", "-")))
    return [{"id": 0, "type": "company", "name": c.name, "username": c.slug.replace("-", "_"), "slug": c.slug,
             "avatar_url": _media(c.logo), "verified": c.status == Company.APPROVED, "connected": False}
            for c in qs.order_by("-status", "name")[:3]]


def _meta_out(m):
    people = {u.pk: u for u in U.objects.filter(pk__in=m.tagged or [])}
    return {"feeling": FEELINGS.get(m.feeling, ""), "feeling_key": m.feeling, "place": m.place,
            "tagged": [_person(people[i]) for i in (m.tagged or []) if i in people], "bg": m.bg, "fg": m.fg, "place_url": _place_url(m.place)}


def _place_url(place):
    try:
        from companies.views import place_url
        return place_url(place)
    except Exception:
        return ""


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
        try:                                            # @bilal_traders -> /company/bilal-traders
            from companies.models import Company
            c = Company.objects.filter(slug=username.lower().replace("_", "-"), hidden=False).first()
            if c:
                return HttpResponseRedirect("/company/" + c.slug)
        except Exception:
            pass
        return HttpResponseRedirect("/feed")
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).first()
        if p and p.slug:
            return HttpResponseRedirect("/in/" + p.slug)
    except Exception:
        pass
    return HttpResponseRedirect("/feed?user=%d" % u.pk)


# ---- reactions on comments, and who reacted (posts and comments) ----
COMMENT_KINDS = ["like", "love", "haha", "wow", "sad", "clap"]


def _people_rows(pairs, viewer):
    """[(user, kind)] -> rows with profile link and whether the viewer is connected."""
    from network.models import ProProfile
    try:
        from feed.views import _connected_ids
        conn = set(_connected_ids(viewer)) if viewer.is_authenticated else set()
    except Exception:
        conn = set()
    slugs = dict(ProProfile.objects.filter(user_id__in=[u.pk for u, _ in pairs]).values_list("user_id", "slug"))
    out = []
    for u, k in pairs:
        d = _person(u); d.update({"kind": k, "slug": slugs.get(u.pk, ""), "connected": u.pk in conn,
                                  "me": viewer.is_authenticated and u.pk == viewer.pk})
        out.append(d)
    return out


@api_view(["GET"])
@permission_classes([AllowAny])
def post_reactors(request, pk):
    from feed.models import Post
    from feed.views import _can_see
    p = Post.objects.filter(pk=pk).first()
    if not p or not _can_see(p, request.user):
        return Response({"detail": "Not found."}, status=404)
    rows = p.reactions.select_related("user").order_by("-created_at")[:300]
    return Response({"people": _people_rows([(r.user, r.kind) for r in rows], request.user)})


def _comment_visible(c, u):
    from feed.views import _can_see
    return c and not c.hidden and _can_see(c.post, u)


@api_view(["GET"])
@permission_classes([AllowAny])
def comment_counts(request):
    """?ids=1,2,3 : reaction counts, the top kinds and your own reaction, for comments you can see."""
    from django.db.models import Count
    from feed.models import Comment
    ids = [int(x) for x in re.findall(r"\d+", str(request.GET.get("ids") or ""))[:100]]
    ok = [c.id for c in Comment.objects.filter(pk__in=ids).select_related("post") if _comment_visible(c, request.user)]
    out = {i: {"count": 0, "top": [], "mine": ""} for i in ok}
    for row in CommentReaction.objects.filter(comment_id__in=ok).values("comment_id", "kind").annotate(n=Count("id")).order_by("-n"):
        o = out[row["comment_id"]]; o["count"] += row["n"]
        if len(o["top"]) < 3: o["top"].append(row["kind"])
    if request.user.is_authenticated:
        for cid, k in CommentReaction.objects.filter(comment_id__in=ok, user=request.user).values_list("comment_id", "kind"):
            out[cid]["mine"] = k
    return Response({"comments": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_react(request, pk):
    """{kind} to react (or change), {kind: ""} to remove. The comment's writer is told about a new reaction."""
    from feed.models import Comment
    c = Comment.objects.filter(pk=pk).select_related("post", "author").first()
    if not _comment_visible(c, request.user):
        return Response({"detail": "Not found."}, status=404)
    kind = str(request.data.get("kind") or "")
    old = CommentReaction.objects.filter(comment=c, user=request.user).first()
    if not kind:
        if old: old.delete()
    elif kind in COMMENT_KINDS:
        if old:
            old.kind = kind; old.save(update_fields=["kind"])
        else:
            CommentReaction.objects.create(comment=c, user=request.user, kind=kind)
            if c.author_id != request.user.pk:
                try:
                    from network.views import _name
                    from notifications.views import notify
                    notify(c.author, "reaction", "%s reacted to your comment." % _name(request.user), "/post/%d" % c.post_id)
                except Exception:
                    pass
    else:
        return Response({"detail": "Unknown reaction."}, status=400)
    n = CommentReaction.objects.filter(comment=c).count()
    return Response({"count": n, "mine": kind})


@api_view(["GET"])
@permission_classes([AllowAny])
def comment_reactors(request, pk):
    from feed.models import Comment
    c = Comment.objects.filter(pk=pk).select_related("post").first()
    if not _comment_visible(c, request.user):
        return Response({"detail": "Not found."}, status=404)
    rows = CommentReaction.objects.filter(comment=c).select_related("user").order_by("-created_at")[:300]
    return Response({"people": _people_rows([(r.user, r.kind) for r in rows], request.user)})



@api_view(["GET"])
@permission_classes([AllowAny])
def card_owner(request, slug):
    """Is the person looking at this card its owner? (for the Edit button on the card page)"""
    from bizcards.models import Card
    c = Card.objects.filter(slug=slug).first()
    f = {x.name for x in Card._meta.fields}
    own = "owner" if "owner" in f else ("user" if "user" in f else None)
    mine = bool(c and own and request.user.is_authenticated and getattr(c, own + "_id") == request.user.pk)
    return Response({"mine": mine, "edit": ("/cards?edit=%d" % c.id) if mine else ""})



@api_view(["GET"])
@permission_classes([AllowAny])
def card_of(request, slug):
    """The digital card (if any) of the member whose XpertConnect profile this is."""
    from bizcards.models import Card
    from network.models import ProProfile
    p = ProProfile.objects.filter(slug=slug).first()
    f = {x.name for x in Card._meta.fields}
    own = "owner" if "owner" in f else ("user" if "user" in f else None)
    if not p or not own:
        return Response({"card": ""})
    qs = Card.objects.filter(**{own: p.user})
    if "hidden" in f: qs = qs.filter(hidden=False)
    if "active" in f: qs = qs.filter(active=True)
    c = qs.order_by("-id").first()
    return Response({"card": ("/c/" + c.slug) if c else ""})
