"""Social extras API (/api/social/): saved posts, reposts, who viewed my profile and my stats, followed and trending hashtags,
and "download my data"."""
import hashlib
import json
import re
from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import ProfileView, Repost, SavedPost, SocialSetting, TagFollow

User = get_user_model()
TAG = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,49}$")
TAG_IN_TEXT = re.compile(r"(?:^|[\s(])#([A-Za-z][A-Za-z0-9_]{1,49})")
SITE = "https://xpertcreation.com"
MARK = "\U0001F501 Reposted: "


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _Post():
    from feed.models import Post
    return Post


def _can_see(p, u):
    try:
        from feed.views import _can_see as cs
        return cs(p, u)
    except Exception:
        return p.visibility == "public" and not p.hidden


def _media(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p and not str(p).startswith(("http", "/")) else (p or "")


def _who(u):
    try:
        from accounts.views import avatar_url
        av = avatar_url(getattr(u, "avatar", "")) or ""
    except Exception:
        av = ""
    slug, head = "", ""
    try:
        from network.models import ProProfile
        pp = ProProfile.objects.filter(user=u).exclude(visibility="hidden").first()
        if pp:
            slug, head = pp.slug, pp.headline
    except Exception:
        pass
    return {"id": u.pk, "name": (getattr(u, "full_name", "") or getattr(u, "username", "") or "Member").strip(), "avatar": av, "slug": slug, "headline": head}


def _mini(p):
    return {"id": p.id, "body": (p.body or "")[:400], "image": _media((p.images or [None])[0]) if p.images else "", "author": _who(p.author),
            "when": timezone.localtime(p.created_at).strftime("%d %b %Y"), "reactions": p.reactions_count, "comments": p.comments_count}


# ---------------------------------------------------------------- saved posts
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def saved_list(request):
    rows = SavedPost.objects.filter(user=request.user).select_related("post__author").order_by("-created_at")[:200]
    return Response({"posts": [dict(_mini(s.post), saved=s.created_at.isoformat()) for s in rows if _can_see(s.post, request.user)]})


@api_view(["GET"])
@permission_classes([AllowAny])
def saved_status(request):
    ids = [int(x) for x in str(request.GET.get("ids") or "").split(",") if x.isdigit()][:60]
    if not request.user.is_authenticated or not ids:
        return Response({"saved": [], "reposts": {}})
    rc = Counter(Repost.objects.filter(original_id__in=ids).values_list("original_id", flat=True))
    return Response({"saved": list(SavedPost.objects.filter(user=request.user, post_id__in=ids).values_list("post_id", flat=True)),
                     "reposts": {str(k): v for k, v in rc.items()}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def saved_toggle(request, pid):
    p = _Post().objects.filter(pk=pid).first()
    if not p or not _can_see(p, request.user):
        return _err("Post not found.", 404)
    s = SavedPost.objects.filter(user=request.user, post=p).first()
    if s:
        s.delete()
        return Response({"saved": False})
    if SavedPost.objects.filter(user=request.user).count() >= 1000:
        return _err("You have 1,000 saved posts. Remove some first.")
    SavedPost.objects.get_or_create(user=request.user, post=p)
    return Response({"saved": True})


# ---------------------------------------------------------------- reposts
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def repost(request, pid):
    u = request.user
    Post = _Post()
    p = Post.objects.filter(pk=pid).select_related("author").first()
    if not p or not _can_see(p, u) or p.hidden:
        return _err("Post not found.", 404)
    if getattr(u, "is_blocked", False):
        return _err("Your account cannot post.", 403)
    orig = getattr(p, "repost_of", None)
    if orig:                                   # reposting a repost shares the original
        p = orig.original
    if Repost.objects.filter(user=u, original=p, created_at__gte=timezone.now() - timedelta(hours=24)).exists():
        return _err("You reposted this today already.")
    if Repost.objects.filter(user=u, created_at__gte=timezone.now() - timedelta(hours=1)).count() >= 10:
        return _err("Too many reposts in one hour. Try later.")
    text = re.sub(r"\n{3,}", "\n\n", str(request.data.get("text") or "").replace("\r", "")).strip()[:2500]
    vis = request.data.get("visibility") if request.data.get("visibility") in ("public", "members", "connections") else "members"
    if p.visibility == "connections":
        vis = "connections"
    elif p.visibility == "members" and vis == "public":
        vis = "members"
    body = (text + "\n\n" if text else "") + MARK + SITE + "/post/%d" % p.id
    new = Post.objects.create(author=u, body=body, visibility=vis)
    Repost.objects.create(user=u, post=new, original=p)
    if p.author_id != u.pk:
        try:
            from notifications.views import notify
            notify(p.author, "repost", "%s reposted your post." % _who(u)["name"], "/post/%d" % new.id)
        except Exception:
            pass
    return Response({"id": new.id, "visibility": vis})


@api_view(["GET"])
@permission_classes([AllowAny])
def embed(request):
    """Small cards of original posts shown inside reposts. Only posts this person may see."""
    ids = [int(x) for x in str(request.GET.get("ids") or "").split(",") if x.isdigit()][:40]
    out = {}
    for p in _Post().objects.filter(pk__in=ids).select_related("author"):
        if _can_see(p, request.user) and not p.hidden:
            out[str(p.id)] = _mini(p)
    return Response({"posts": out})


# ---------------------------------------------------------------- profile views and stats
@api_view(["POST"])
@permission_classes([AllowAny])
def view(request, uid):
    u = request.user
    if u.is_authenticated and u.pk == uid:
        return Response({"ok": True})
    if not User.objects.filter(pk=uid, is_active=True).exists():
        return Response({"ok": False})
    private = False
    if u.is_authenticated:
        s = SocialSetting.objects.filter(user=u).first()
        private = bool(s and s.private_views)
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "").split(",")[0].strip()
    if u.is_authenticated and not private:
        vkey, viewer = str(u.pk), u
    else:
        vkey, viewer = "anon:" + hashlib.sha1(((str(u.pk) if u.is_authenticated else "") + ip + settings.SECRET_KEY[:8]).encode()).hexdigest()[:20], None
    day = timezone.localdate()
    try:
        obj, made = ProfileView.objects.get_or_create(owner_id=uid, vkey=vkey, day=day, defaults={"viewer": viewer})
        if not made:
            ProfileView.objects.filter(pk=obj.pk).update(n=obj.n + 1, last=timezone.now())
    except IntegrityError:
        pass
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats(request):
    u, now = request.user, timezone.now()
    today = timezone.localdate()
    pv = ProfileView.objects.filter(owner=u)
    d7, d30, d90 = today - timedelta(days=6), today - timedelta(days=29), today - timedelta(days=89)
    series = {r["day"].isoformat(): 0 for r in []}
    by_day = Counter()
    for day, n in pv.filter(day__gte=d30).values_list("day", "vkey"):
        by_day[day.isoformat()] += 1
    series = [{"day": (d30 + timedelta(days=i)).isoformat(), "n": by_day.get((d30 + timedelta(days=i)).isoformat(), 0)} for i in range(30)]
    seen, viewers = set(), []
    for r in pv.filter(day__gte=d30, viewer__isnull=False).select_related("viewer").order_by("-last")[:200]:
        if r.viewer_id in seen or not r.viewer or not r.viewer.is_active:
            continue
        seen.add(r.viewer_id)
        viewers.append(dict(_who(r.viewer), when=r.last.isoformat()))
        if len(viewers) >= 40:
            break
    out = {"views": {"d7": pv.filter(day__gte=d7).count(), "d30": pv.filter(day__gte=d30).count(), "d90": pv.filter(day__gte=d90).count()},
           "series": series, "viewers": viewers, "hidden_viewers": pv.filter(day__gte=d30, viewer__isnull=True).count()}
    Post = _Post()
    mine = Post.objects.filter(author=u, hidden=False)
    since = now - timedelta(days=30)
    try:
        from feed.models import Comment, Reaction
        out["posts"] = {"d30": mine.filter(created_at__gte=since).count(), "all": mine.count(),
                        "reactions_d30": Reaction.objects.filter(post__author=u, created_at__gte=since).exclude(user=u).count(),
                        "comments_d30": Comment.objects.filter(post__author=u, created_at__gte=since).exclude(author=u).count(),
                        "saves": SavedPost.objects.filter(post__author=u).exclude(user=u).count(),
                        "reposts": Repost.objects.filter(original__author=u).exclude(user=u).count()}
        top = mine.order_by("-reactions_count", "-comments_count")[:3]
        out["top_posts"] = [_mini(p) for p in top if p.reactions_count or p.comments_count]
    except Exception:
        out["posts"] = {}
    try:
        from network.models import Connection, Follow
        out["network"] = {"followers": Follow.objects.filter(following=u).count(), "followers_d30": Follow.objects.filter(following=u, created_at__gte=since).count(),
                          "connections": Connection.objects.filter(Q(from_user=u) | Q(to_user=u), state="accepted").count()}
    except Exception:
        out["network"] = {}
    try:
        from brandkit.models import ProfileButton
        pb = ProfileButton.objects.filter(user=u).first()
        out["buttons"] = {"all": pb.clicks if pb else 0, "d30": sum(n for k, n in (pb.daily or {}).items() if k >= d30.isoformat()) if pb else 0}
    except Exception:
        out["buttons"] = None
    s = SocialSetting.objects.filter(user=u).first()
    out["private_views"] = bool(s and s.private_views)
    return Response(out)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def privacy(request):
    s, _ = SocialSetting.objects.get_or_create(user=request.user)
    if request.method == "POST" and "private_views" in request.data:
        s.private_views = str(request.data.get("private_views")).lower() in ("true", "1")
        s.save()
    return Response({"private_views": s.private_views})


# ---------------------------------------------------------------- hashtags
def tag_q(u):
    """Posts with any hashtag this member follows (used by the feed's Following tab)."""
    tags = list(TagFollow.objects.filter(user=u).values_list("tag", flat=True)[:50])
    if not tags:
        return None
    return Q(body__iregex=r"(^|[\s(])#(%s)([^A-Za-z0-9_]|$)" % "|".join(re.escape(t) for t in tags))


def _counts(since, until):
    c = Counter()
    for body in _Post().objects.filter(visibility="public", hidden=False, created_at__gte=since, created_at__lt=until).values_list("body", flat=True)[:5000]:
        c.update({t.lower() for t in TAG_IN_TEXT.findall(body or "")})
    return c


@api_view(["GET"])
@permission_classes([AllowAny])
def trending(request):
    hit = cache.get("social:trending")
    if hit is None:
        now = timezone.now()
        cur, prev = _counts(now - timedelta(days=7), now), _counts(now - timedelta(days=14), now - timedelta(days=7))
        skip = {"xpertcreation", "pakistan"}
        rows = []
        for t, n in cur.most_common(40):
            if t in skip and len(cur) > 12:
                continue
            p = prev.get(t, 0)
            rows.append({"tag": t, "posts": n, "up": n > p, "new": p == 0, "score": n + max(0, n - p)})
        rows.sort(key=lambda r: -r["score"])
        hit = rows[:12]
        cache.set("social:trending", hit, 1800)
    return Response({"tags": hit})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_tags(request):
    return Response({"tags": list(TagFollow.objects.filter(user=request.user).order_by("tag").values_list("tag", flat=True))})


@api_view(["GET"])
@permission_classes([AllowAny])
def tag_status(request, name):
    if not TAG.match(name):
        return _err("Not a hashtag.", 404)
    t = name.lower()
    return Response({"tag": t, "followers": TagFollow.objects.filter(tag=t).count(),
                     "following": request.user.is_authenticated and TagFollow.objects.filter(user=request.user, tag=t).exists()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tag_follow(request, name):
    if not TAG.match(name):
        return _err("Not a hashtag.", 404)
    t = name.lower()
    f = TagFollow.objects.filter(user=request.user, tag=t).first()
    if f:
        f.delete()
    else:
        if TagFollow.objects.filter(user=request.user).count() >= 50:
            return _err("You follow 50 hashtags. Unfollow some first.")
        TagFollow.objects.get_or_create(user=request.user, tag=t)
    return Response({"tag": t, "following": not f, "followers": TagFollow.objects.filter(tag=t).count()})


# ---------------------------------------------------------------- download my data
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export(request):
    u = request.user
    key = "social:export:%d" % u.pk
    if cache.get(key):
        return _err("You can download your data 3 times an hour. Try a bit later.", 429)
    cache.set(key, 1, 1200)
    data = {"site": "XpertCreation", "made": timezone.now().isoformat(),
            "account": {k: str(getattr(u, k, "") or "") for k in ("email", "username", "full_name", "phone", "date_joined", "last_login")}}
    try:
        from network.models import Connection, Education, Experience, Follow, ProProfile, Skill
        p = ProProfile.objects.filter(user=u).first()
        if p:
            data["profile"] = {k: getattr(p, k) for k in ("slug", "headline", "about", "city", "state", "country", "website", "visibility", "open_to_work", "open_to")}
            data["profile"]["socials"] = p.socials
            data["skills"] = list(Skill.objects.filter(profile=p).values_list("name", flat=True))
            for key, M in (("experience", Experience), ("education", Education)):
                data[key] = [{k: str(v) for k, v in e.items() if k not in ("id", "profile_id")} for e in M.objects.filter(profile=p).values()]
        data["following"] = [str(x) for x in Follow.objects.filter(follower=u).values_list("following__full_name", flat=True)]
        data["connections"] = Connection.objects.filter(Q(from_user=u) | Q(to_user=u), state="accepted").count()
    except Exception:
        pass
    try:
        from feed.models import Comment
        Post = _Post()
        data["posts"] = [{"id": p.id, "body": p.body, "images": [SITE + _media(i) for i in (p.images or [])], "visibility": p.visibility,
                          "when": p.created_at.isoformat()} for p in Post.objects.filter(author=u).order_by("id")]
        data["comments"] = [{"post": c.post_id, "body": c.body, "when": c.created_at.isoformat()} for c in Comment.objects.filter(author=u).order_by("id")[:5000]]
    except Exception:
        pass
    data["saved_posts"] = [SITE + "/post/%d" % i for i in SavedPost.objects.filter(user=u).values_list("post_id", flat=True)]
    data["hashtags_followed"] = list(TagFollow.objects.filter(user=u).values_list("tag", flat=True))
    r = HttpResponse(json.dumps(data, ensure_ascii=False, indent=1, default=str), content_type="application/json; charset=utf-8")
    r["Content-Disposition"] = 'attachment; filename="xpertcreation-my-data-%s.json"' % timezone.localdate().isoformat()
    return r
