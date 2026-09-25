"""Feed: posts with photos, reactions, comments and replies, reports.

Who sees a post: "public" - anyone; "members" - anyone signed in; "connections" - the author's
accepted connections. Moderators and staff see hidden posts and can hide or unhide them.
"""
import os
import secrets

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import REACTIONS, Comment, Post, PostReport, Reaction

KINDS = dict(REACTIONS)
PAGE = 20
MAX_PHOTO = 5 * 1024 * 1024
PHOTOS_PER_DAY = 10
POSTS_PER_DAY = 20


class _UserThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class PostThrottle(_UserThrottle):
    scope = "feed_post"


class ReactThrottle(_UserThrottle):
    scope = "feed_react"


class CommentThrottle(_UserThrottle):
    scope = "feed_comment"


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


def _mod(u):
    return bool(u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _author(u):
    """Name, picture, headline, profile link and blue tick - from the Connect profile when there is one."""
    from network.models import ProProfile
    from network.views import _av, _name, _ticked
    p = ProProfile.objects.filter(user=u).first()
    return {"id": u.pk, "name": _name(u), "avatar_url": _av(u), "slug": p.slug if p else None,
            "headline": p.headline if p else "", "verified": _ticked(p) if p else False}


def _connected_ids(u):
    from network.models import Connection
    rows = Connection.objects.filter(Q(from_user=u) | Q(to_user=u), state=Connection.ACCEPTED).values_list("from_user_id", "to_user_id")
    return {b if a == u.pk else a for a, b in rows}


def _can_see(post, u):
    if post.hidden and not (_mod(u) or (u.is_authenticated and u.pk == post.author_id)):
        return False
    if post.visibility == "public":
        return True
    if not u.is_authenticated:
        return False
    if post.visibility == "members" or u.pk == post.author_id:
        return True
    return post.author_id in _connected_ids(u)


def _url(p):
    return settings.MEDIA_URL.rstrip("/") + "/" + p


def _out(post, u, mine_reaction=None, top=None, authors=None):
    a = (authors or {}).get(post.author_id) or _author(post.author)
    return {"id": post.id, "author": a, "body": post.body, "images": [_url(i) for i in post.images or []],
            "visibility": post.visibility, "reactions": post.reactions_count, "comments": post.comments_count,
            "top": top or [], "mine": mine_reaction or "", "hidden": post.hidden,
            "can_edit": u.is_authenticated and u.pk == post.author_id, "can_moderate": _mod(u),
            "when": post.created_at.strftime("%d %b %Y, %H:%M"), "edited": bool(post.edited_at)}


def _visible_qs(u):
    qs = Post.objects.select_related("author")
    if not _mod(u):
        qs = qs.filter(hidden=False) if not u.is_authenticated else qs.filter(Q(hidden=False) | Q(author=u))
    if not u.is_authenticated:
        return qs.filter(visibility="public")
    return qs.filter(Q(visibility__in=["public", "members"]) | Q(author=u) |
                     Q(visibility="connections", author_id__in=_connected_ids(u)))


def _save_photo(f, user_id):
    from PIL import Image, ImageOps
    if f.size > MAX_PHOTO:
        raise ValueError("A photo is over 5 MB.")
    try:
        im = Image.open(f)
        fmt = im.format
        im.load()
    except Exception:
        raise ValueError("One of the files is not a photo we can read.")
    if fmt not in ("JPEG", "PNG", "WEBP", "GIF"):
        raise ValueError("Use JPG, PNG or WebP photos.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1600, 1600))
    rel = "feed/%d/%s.webp" % (user_id, secrets.token_hex(12))
    full = os.path.join(settings.MEDIA_ROOT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    try:
        im.save(full, "WEBP", quality=80, method=4)
    except Exception:
        rel = rel[:-5] + ".jpg"
        full = os.path.join(settings.MEDIA_ROOT, rel)
        im.save(full, "JPEG", quality=82, optimize=True)
    return rel


def _page(posts, u):
    posts = list(posts)
    ids = [p.id for p in posts]
    mine = dict(Reaction.objects.filter(post_id__in=ids, user=u).values_list("post_id", "kind")) if u.is_authenticated else {}
    tops = {}
    for row in Reaction.objects.filter(post_id__in=ids).values("post_id", "kind").annotate(n=Count("id")).order_by("-n"):
        tops.setdefault(row["post_id"], [])
        if len(tops[row["post_id"]]) < 3:
            tops[row["post_id"]].append(row["kind"])
    authors = {}
    for p in posts:
        if p.author_id not in authors:
            authors[p.author_id] = _author(p.author)
    return [_out(p, u, mine.get(p.id), tops.get(p.id), authors) for p in posts]


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def posts(request):
    u = request.user
    if request.method == "GET":
        qs = _visible_qs(u)
        scope = request.GET.get("scope") or "all"
        if scope == "mine":
            if not u.is_authenticated:
                return Response({"posts": [], "more": False})
            qs = qs.filter(author=u)
        elif scope == "following":
            if not u.is_authenticated:
                return Response({"posts": [], "more": False})
            from network.models import Follow
            ids = set(Follow.objects.filter(follower=u).values_list("following_id", flat=True)) | _connected_ids(u) | {u.pk}
            qs = qs.filter(author_id__in=ids)
        elif scope.startswith("user:"):
            from network.models import ProProfile
            p = ProProfile.objects.filter(slug=scope[5:]).first()
            qs = qs.filter(author_id=p.user_id) if p else qs.none()
        try:
            before = int(request.GET.get("before") or 0)
        except ValueError:
            before = 0
        if before:
            qs = qs.filter(id__lt=before)
        rows = list(qs.order_by("-id")[:PAGE + 1])
        return Response({"posts": _page(rows[:PAGE], u), "more": len(rows) > PAGE})

    # ---- a new post ----
    if not u.is_authenticated:
        return _err("Sign in to post.", status.HTTP_401_UNAUTHORIZED)
    if getattr(u, "is_blocked", False):
        return _err("Your account cannot post.", status.HTTP_403_FORBIDDEN)
    for t in (PostThrottle(),):
        if not t.allow_request(request, None):
            return _err("You are posting too fast. Try again in a little while.", status.HTTP_429_TOO_MANY_REQUESTS)
    today = timezone.localdate()
    if Post.objects.filter(author=u, created_at__date=today).count() >= POSTS_PER_DAY:
        return _err("You have posted %d times today. Try again tomorrow." % POSTS_PER_DAY)
    body = str(request.data.get("body") or "").strip()[:3000]
    vis = request.data.get("visibility") or "members"
    if vis not in dict(Post.VISIBILITY):
        vis = "members"
    files = request.FILES.getlist("images")[:4]
    if files:
        used = sum(len(p.images or []) for p in Post.objects.filter(author=u, created_at__date=today))
        if used + len(files) > PHOTOS_PER_DAY:
            return _err("You can add %d photos a day." % PHOTOS_PER_DAY)
    if not body and not files:
        return _err("Write something or add a photo.")
    saved = []
    try:
        for f in files:
            saved.append(_save_photo(f, u.pk))
    except ValueError as e:
        for s in saved:
            try:
                os.remove(os.path.join(settings.MEDIA_ROOT, s))
            except OSError:
                pass
        return _err(str(e))
    post = Post.objects.create(author=u, body=body, images=saved, visibility=vis)
    return Response({"post": _page([post], u)[0]}, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def post_detail(request, pk):
    u = request.user
    post = Post.objects.select_related("author").filter(id=pk).first()
    if not post or not _can_see(post, u):
        return _err("This post is not available.", status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response({"post": _page([post], u)[0]})
    if not u.is_authenticated:
        return _err("Sign in first.", status.HTTP_401_UNAUTHORIZED)
    if request.method == "DELETE":
        if u.pk != post.author_id and not _mod(u):
            return _err("Not yours.", status.HTTP_403_FORBIDDEN)
        for s in post.images or []:
            try:
                os.remove(os.path.join(settings.MEDIA_ROOT, s))
            except OSError:
                pass
        post.delete()
        return Response({"deleted": True})
    d = request.data
    if "hidden" in d:
        if not _mod(u):
            return _err("Only moderators can hide posts.", status.HTTP_403_FORBIDDEN)
        post.hidden = bool(d.get("hidden"))
        post.save(update_fields=["hidden"])
    if "body" in d or "visibility" in d:
        if u.pk != post.author_id:
            return _err("Not yours.", status.HTTP_403_FORBIDDEN)
        if "body" in d:
            body = str(d.get("body") or "").strip()[:3000]
            if not body and not post.images:
                return _err("A post cannot be empty.")
            post.body = body
        if d.get("visibility") in dict(Post.VISIBILITY):
            post.visibility = d["visibility"]
        post.edited_at = timezone.now()
        post.save(update_fields=["body", "visibility", "edited_at"])
    return Response({"post": _page([post], u)[0]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ReactThrottle])
def react(request, pk):
    """body: { kind: "like" | ... } to set or change, { kind: "" } to remove."""
    u = request.user
    post = Post.objects.filter(id=pk).first()
    if not post or not _can_see(post, u):
        return _err("This post is not available.", status.HTTP_404_NOT_FOUND)
    kind = request.data.get("kind") or ""
    old = Reaction.objects.filter(post=post, user=u).first()
    if not kind:
        if old:
            old.delete()
            Post.objects.filter(id=post.id, reactions_count__gt=0).update(reactions_count=F("reactions_count") - 1)
    elif kind not in KINDS:
        return _err("Unknown reaction.")
    elif old:
        old.kind = kind
        old.save(update_fields=["kind"])
    else:
        Reaction.objects.create(post=post, user=u, kind=kind)
        Post.objects.filter(id=post.id).update(reactions_count=F("reactions_count") + 1)
        key = "feed_react_note:%d" % post.id
        if post.author_id != u.pk and not cache.get(key):          # at most one bell an hour per post
            cache.set(key, 1, 3600)
            from network.views import _name
            from notifications.views import notify
            notify(post.author, "reaction", "%s reacted to your post." % _name(u), "/post/%d" % post.id)
    post.refresh_from_db(fields=["reactions_count"])
    return Response({"mine": kind, "reactions": post.reactions_count})


def _comment_out(c, u, authors):
    if c.author_id not in authors:
        authors[c.author_id] = _author(c.author)
    return {"id": c.id, "parent": c.parent_id, "author": authors[c.author_id], "body": c.body, "hidden": c.hidden,
            "when": c.created_at.strftime("%d %b, %H:%M"),
            "can_delete": u.is_authenticated and (u.pk == c.author_id or _mod(u))}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def comments(request, pk):
    u = request.user
    post = Post.objects.filter(id=pk).first()
    if not post or not _can_see(post, u):
        return _err("This post is not available.", status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        qs = post.comments.select_related("author")
        if not _mod(u):
            qs = qs.filter(hidden=False)
        authors = {}
        return Response({"comments": [_comment_out(c, u, authors) for c in qs[:300]]})
    if not u.is_authenticated:
        return _err("Sign in to comment.", status.HTTP_401_UNAUTHORIZED)
    if not CommentThrottle().allow_request(request, None):
        return _err("You are commenting too fast.", status.HTTP_429_TOO_MANY_REQUESTS)
    body = str(request.data.get("body") or "").strip()[:1000]
    if not body:
        return _err("Write a comment first.")
    parent = None
    if request.data.get("parent"):
        parent = post.comments.filter(id=request.data.get("parent")).first()
        if parent and parent.parent_id:          # replies stay one level deep
            parent = parent.parent
    c = Comment.objects.create(post=post, author=u, parent=parent, body=body)
    Post.objects.filter(id=post.id).update(comments_count=F("comments_count") + 1)
    from network.views import _name
    from notifications.views import notify
    told = set()
    if post.author_id != u.pk:
        notify(post.author, "comment", "%s commented on your post." % _name(u), "/post/%d" % post.id)
        told.add(post.author_id)
    if parent and parent.author_id != u.pk and parent.author_id not in told:
        notify(parent.author, "comment", "%s replied to your comment." % _name(u), "/post/%d" % post.id)
    return Response({"comment": _comment_out(c, u, {})}, status=status.HTTP_201_CREATED)


@api_view(["DELETE", "PATCH"])
@permission_classes([IsAuthenticated])
def comment_delete(request, pk):
    u = request.user
    c = Comment.objects.filter(id=pk).first()
    if not c:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    if request.method == "PATCH":                     # moderators hide or unhide
        if not _mod(u):
            return _err("Only moderators can hide comments.", status.HTTP_403_FORBIDDEN)
        c.hidden = bool(request.data.get("hidden"))
        c.save(update_fields=["hidden"])
        return Response({"hidden": c.hidden})
    if u.pk != c.author_id and not _mod(u) and u.pk != c.post.author_id:
        return _err("Not yours.", status.HTTP_403_FORBIDDEN)
    n = 1 + c.replies.count()
    post_id = c.post_id
    c.delete()
    Post.objects.filter(id=post_id).update(comments_count=F("comments_count") - n)
    Post.objects.filter(id=post_id, comments_count__lt=0).update(comments_count=0)
    return Response({"deleted": n})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([CommentThrottle])
def report(request, pk):
    post = Post.objects.filter(id=pk).first()
    if not post or not _can_see(post, request.user):
        return _err("This post is not available.", status.HTTP_404_NOT_FOUND)
    reason = request.data.get("reason")
    if reason not in dict(PostReport.REASONS):
        return _err("Pick a reason.")
    cid = request.data.get("comment")
    comment = post.comments.filter(id=cid).first() if cid else None
    PostReport.objects.create(post=post, comment=comment, reporter=request.user, reason=reason,
                              note=str(request.data.get("note") or "").strip()[:500])
    from notifications.views import notify_admins
    notify_admins("report", "A post was reported (%s)." % reason, "/admin/feed/postreport/")
    return Response({"ok": True})
