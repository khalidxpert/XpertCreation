"""/api/xsocial/ - step 3: recommendations, featured, company reviews, events, articles and newsletter subscriptions."""
import os
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Article, CompanyReview, Event, EventRsvp, Featured, Recommendation, Subscription
from .views import _avatar, _err, _friends, _name, _slug, _staff, _txt

SITE = "https://xpertcreation.com"


def _who(u):
    p = getattr(u, "pro", None)
    return {"id": u.pk, "name": _name(u), "slug": _slug(u), "avatar": _avatar(u), "headline": getattr(p, "headline", "") if p else "",
            "verified": bool(getattr(p, "verified", False)) if p else False}


def _profile_user(slug):
    from network.models import ProProfile
    s = str(slug or "").strip().strip("/").split("/in/")[-1]
    p = ProProfile.objects.filter(slug__iexact=s).select_related("user").first() if s else None
    return p.user if p else None


def _blocked(a, b):
    try:
        from .privacy import blocked_between
        return a and b and blocked_between(a, b)
    except Exception:
        return False


def _notify(u, text, link):
    try:
        from notifications.views import notify
        notify(u, "social", text[:200], link)
    except Exception:
        pass


def _email_ok(u):
    return bool(getattr(u, "is_email_verified", True))


def _save_cover(f, folder, uid):
    from PIL import Image, ImageOps
    if f.size > 6 * 1024 * 1024:
        raise ValueError("The picture is over 6 MB.")
    try:
        im = Image.open(f); im.load()
    except Exception:
        raise ValueError("That file is not a picture we can read.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1600, 1000))
    rel = "xsocial/%s/%d_%s.webp" % (folder, uid, secrets.token_hex(8))
    full = os.path.join(str(settings.MEDIA_ROOT), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=82)
    return rel


def _media(rel):
    return ("/media/" + rel) if rel else ""


# ---------------------------------------------------------------- recommendations
def _rec_out(r):
    return {"id": r.id, "by": _who(r.author), "relation": r.relation, "body": r.body, "status": r.status, "when": r.created_at.isoformat()}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def recs(request):
    u = request.user
    if request.method == "GET":
        owner = _profile_user(request.GET.get("slug"))
        if not owner or (u.is_authenticated and _blocked(u.pk, owner.pk)):
            return Response({"shown": [], "pending": [], "mine": False})
        me = u.is_authenticated and u.pk == owner.pk
        rows = Recommendation.objects.filter(to=owner).select_related("author").order_by("-id")
        out = {"shown": [_rec_out(r) for r in rows if r.status == "shown"], "mine": me, "can_write": False}
        if me:
            out["pending"] = [_rec_out(r) for r in rows if r.status == "pending"]
            out["hidden"] = [_rec_out(r) for r in rows if r.status == "hidden"]
        elif u.is_authenticated:
            out["can_write"] = owner.pk in _friends(u) and not Recommendation.objects.filter(author=u, to=owner).exists()
            out["wrote"] = Recommendation.objects.filter(author=u, to=owner).exists()
        return Response(out)
    if not u.is_authenticated:
        return _err("Sign in first.", 403)
    to = _profile_user(request.data.get("slug"))
    if not to or to.pk == u.pk:
        return _err("Profile not found.", 404)
    if to.pk not in _friends(u):
        return _err("You can recommend your connections only.", 403)
    body = str(request.data.get("body") or "").strip()[:1500]
    if len(body) < 30:
        return _err("Write a few lines (30+ letters) about working with them.")
    r, made = Recommendation.objects.get_or_create(author=u, to=to, defaults={"relation": _txt(request.data.get("relation"), 120), "body": body})
    if not made:
        return _err("You already wrote a recommendation for them.")
    _notify(to, "%s wrote you a recommendation. Accept it to show it on your profile." % _name(u), "/in/%s#recs" % _slug(to))
    return Response(_rec_out(r))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rec_act(request, rid, act):
    u = request.user
    r = Recommendation.objects.filter(pk=rid).first()
    if not r:
        return _err("Not found.", 404)
    if act in ("show", "hide") and r.to_id == u.pk:
        r.status = "shown" if act == "show" else "hidden"; r.save(update_fields=["status"])
        if act == "show":
            _notify(r.author, "%s added your recommendation to their profile." % _name(u), "/in/%s#recs" % _slug(u))
        return Response(_rec_out(r))
    if act == "delete" and u.pk in (r.to_id, r.author_id):
        r.delete(); return Response({"deleted": True})
    return _err("Not allowed.", 403)


# ---------------------------------------------------------------- featured
def _feat_out(f):
    d = {"id": f.id, "title": f.title, "url": f.url, "note": f.note, "kind": "post" if f.post_id else "link"}
    if f.post_id:
        p = f.post
        d.update({"post": p.id, "url": "/post/%d" % p.id, "title": f.title or (p.body[:80] or "Post"), "note": p.body[:160],
                  "image": ("/media/" + p.images[0]) if p.images else ""})
    return d


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def featured(request):
    u = request.user
    if request.method == "GET":
        owner = _profile_user(request.GET.get("slug"))
        if not owner or (u.is_authenticated and _blocked(u.pk, owner.pk)):
            return Response({"items": [], "mine": False})
        rows = [f for f in Featured.objects.filter(user=owner).select_related("post")
                if not f.post_id or (not f.post.hidden and f.post.visibility in ("public", "members"))]
        return Response({"items": [_feat_out(f) for f in rows[:6]], "mine": u.is_authenticated and u.pk == owner.pk})
    if not u.is_authenticated:
        return _err("Sign in first.", 403)
    if Featured.objects.filter(user=u).count() >= 6:
        return _err("You can feature up to 6 things. Remove one first.")
    pid = request.data.get("post")
    if pid:
        from feed.models import Post
        p = Post.objects.filter(pk=pid, author=u, hidden=False).first()
        if not p:
            return _err("You can feature your own posts only.", 404)
        if p.visibility not in ("public", "members"):
            return _err("Only posts shared with Everyone or Members can be featured.")
        if Featured.objects.filter(user=u, post=p).exists():
            return _err("Already featured.")
        f = Featured.objects.create(user=u, post=p)
    else:
        url = str(request.data.get("url") or "").strip()[:400]
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", url):
            return _err("Paste a full link that starts with https://")
        title = _txt(request.data.get("title"), 120)
        if not title:
            return _err("Give the link a title.")
        f = Featured.objects.create(user=u, url=url, title=title, note=_txt(request.data.get("note"), 200))
    return Response(_feat_out(f))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def featured_remove(request, fid):
    n = Featured.objects.filter(pk=fid, user=request.user).delete()[0]
    return Response({"deleted": n})


# ---------------------------------------------------------------- company reviews
def _company(slug):
    from companies.models import Company
    return Company.objects.filter(slug=str(slug or "")[:60], hidden=False).first()


def _rev_out(r, u):
    return {"id": r.id, "by": _who(r.user), "stars": r.stars, "body": r.body, "reply": r.reply, "when": r.created_at.isoformat(),
            "mine": u.is_authenticated and u.pk == r.user_id, "hidden": r.hidden}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def coreviews(request):
    u = request.user
    if request.method == "GET":
        c = _company(request.GET.get("slug"))
        if not c:
            return _err("Not found.", 404)
        qs = CompanyReview.objects.filter(company=c).select_related("user")
        if not _staff(u):
            qs = qs.filter(hidden=False)
        agg = qs.filter(hidden=False).aggregate(a=Avg("stars"), n=Count("id"))
        owner = u.is_authenticated and u.pk == c.owner_id
        dist = {i: qs.filter(hidden=False, stars=i).count() for i in range(1, 6)}
        return Response({"avg": round(agg["a"] or 0, 1), "count": agg["n"], "dist": dist, "reviews": [_rev_out(r, u) for r in qs[:100]],
                         "owner": owner, "staff": _staff(u), "signed": u.is_authenticated,
                         "can_review": u.is_authenticated and not owner and _email_ok(u)})
    if not u.is_authenticated:
        return _err("Sign in to write a review.", 403)
    c = _company(request.data.get("slug"))
    if not c:
        return _err("Not found.", 404)
    if c.owner_id == u.pk:
        return _err("You can't review your own business.")
    if not _email_ok(u):
        return _err("Verify your email first.", 403)
    try:
        stars = int(request.data.get("stars"))
    except (TypeError, ValueError):
        stars = 0
    if not 1 <= stars <= 5:
        return _err("Choose 1 to 5 stars.")
    body = str(request.data.get("body") or "").strip()[:1500]
    r, made = CompanyReview.objects.update_or_create(company=c, user=u, defaults={"stars": stars, "body": body})
    if made:
        _notify(c.owner, "%s gave %s %d star%s." % (_name(u), c.name, stars, "" if stars == 1 else "s"), "/company/%s#reviews" % c.slug)
    return Response(_rev_out(r, u))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def corev_act(request, rid, act):
    u = request.user
    r = CompanyReview.objects.filter(pk=rid).select_related("company", "user").first()
    if not r:
        return _err("Not found.", 404)
    if act == "reply" and u.pk == r.company.owner_id:
        r.reply = str(request.data.get("reply") or "").strip()[:1000]; r.save(update_fields=["reply", "updated_at"])
        if r.reply:
            _notify(r.user, "%s replied to your review." % r.company.name, "/company/%s#reviews" % r.company.slug)
        return Response(_rev_out(r, u))
    if act == "delete" and (u.pk == r.user_id or _staff(u)):
        r.delete(); return Response({"deleted": True})
    if act in ("hide", "unhide") and _staff(u):
        r.hidden = act == "hide"; r.save(update_fields=["hidden"]); return Response(_rev_out(r, u))
    if act == "report" and u.pk == r.company.owner_id:
        try:
            from notifications.views import notify_admins
            notify_admins("report", "A review on %s was reported by the owner: %s" % (r.company.name, _txt(request.data.get("why"), 150)), "/company/%s#reviews" % r.company.slug)
        except Exception:
            pass
        return Response({"ok": True})
    return _err("Not allowed.", 403)


# ---------------------------------------------------------------- events
def _ev_out(e, u, full=False):
    n = dict(EventRsvp.objects.filter(event=e).values_list("status").annotate(c=Count("id")))
    mine = EventRsvp.objects.filter(event=e, user_id=u.pk).values_list("status", flat=True).first() if u.is_authenticated else None
    d = {"id": e.id, "title": e.title, "host": _who(e.host), "starts": e.starts_at.isoformat(), "ends": e.ends_at.isoformat() if e.ends_at else "",
         "online": e.online, "place": e.place if (not e.online or full) else "", "city": e.city, "cover": _media(e.cover), "cancelled": e.cancelled,
         "going": n.get("going", 0), "interested": n.get("interested", 0), "mine": mine, "host_me": u.is_authenticated and u.pk == e.host_id,
         "link": SITE + "/events#e%d" % e.id}
    if full:
        d["about"] = e.about
        if not (mine or d["host_me"]) and e.online:
            d["place"] = ""                      # the online link shows after you tap Going / Interested
        d["people"] = [_who(r.user) for r in EventRsvp.objects.filter(event=e, status="going").select_related("user")[:30]]
    return d


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def events(request):
    u = request.user
    if request.method == "GET":
        now = timezone.now()
        qs = Event.objects.select_related("host")
        if request.GET.get("mine") and u.is_authenticated:
            ids = EventRsvp.objects.filter(user=u).values_list("event_id", flat=True)
            qs = qs.filter(Q(host=u) | Q(pk__in=ids)).order_by("-starts_at")
        elif request.GET.get("past"):
            qs = qs.filter(starts_at__lt=now - timedelta(hours=6)).order_by("-starts_at")
        else:
            qs = qs.filter(Q(ends_at__gte=now) | Q(ends_at__isnull=True, starts_at__gte=now - timedelta(hours=6)), cancelled=False)
        city = _txt(request.GET.get("city"), 60)
        if city:
            qs = qs.filter(Q(city__iexact=city) | Q(online=True))
        b = set()
        if u.is_authenticated:
            from .privacy import blocked_ids
            b = blocked_ids(u)
        return Response({"events": [_ev_out(e, u) for e in qs[:60] if e.host_id not in b]})
    if not u.is_authenticated:
        return _err("Sign in first.", 403)
    if not _email_ok(u):
        return _err("Verify your email first.", 403)
    d = request.data
    title = _txt(d.get("title"), 120)
    starts = parse_datetime(str(d.get("starts") or ""))
    ends = parse_datetime(str(d.get("ends") or "")) if d.get("ends") else None
    if len(title) < 4:
        return _err("Give the event a name.")
    if not starts or starts < timezone.now() - timedelta(minutes=5):
        return _err("Choose when it starts (in the future).")
    if ends and ends <= starts:
        ends = None
    online = str(d.get("online")).lower() in ("true", "1", "on")
    place = _txt(d.get("place"), 200)
    if not place:
        return _err("Write the address, or the online meeting link.")
    if Event.objects.filter(host=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= 5:
        return _err("You can create 5 events a day.")
    cover = ""
    if request.FILES.get("cover"):
        try:
            cover = _save_cover(request.FILES["cover"], "events", u.pk)
        except ValueError as ex:
            return _err(str(ex))
    e = Event.objects.create(host=u, title=title, about=str(d.get("about") or "").strip()[:3000], starts_at=starts, ends_at=ends,
                             online=online, place=place, city=_txt(d.get("city"), 60), cover=cover)
    EventRsvp.objects.create(event=e, user=u, status="going")
    return Response(_ev_out(e, u, True))


@api_view(["GET"])
@permission_classes([AllowAny])
def event(request, eid):
    e = Event.objects.filter(pk=eid).select_related("host").first()
    if not e or (request.user.is_authenticated and _blocked(request.user.pk, e.host_id)):
        return _err("Event not found.", 404)
    return Response(_ev_out(e, request.user, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def event_act(request, eid, act):
    u = request.user
    e = Event.objects.filter(pk=eid).select_related("host").first()
    if not e:
        return _err("Event not found.", 404)
    if act == "rsvp":
        st = request.data.get("status")
        if e.cancelled:
            return _err("This event was cancelled.")
        if st in ("going", "interested"):
            _, made = EventRsvp.objects.update_or_create(event=e, user=u, defaults={"status": st})
            if made and st == "going" and e.host_id != u.pk:
                _notify(e.host, "%s is going to %s." % (_name(u), e.title), "/events#e%d" % e.id)
        else:
            EventRsvp.objects.filter(event=e, user=u).delete()
        return Response(_ev_out(e, u, True))
    if act == "cancel" and u.pk == e.host_id:
        e.cancelled = True; e.save(update_fields=["cancelled"])
        for r in EventRsvp.objects.filter(event=e).exclude(user=u).select_related("user")[:2000]:
            _notify(r.user, "Cancelled: %s" % e.title, "/events#e%d" % e.id)
        return Response(_ev_out(e, u, True))
    return _err("Not allowed.", 403)


def tick():
    """Every 15 minutes (cron): remind Going / Interested people a day before and an hour before."""
    now = timezone.now(); n = 0
    for e in Event.objects.filter(cancelled=False, reminded_day=False, starts_at__gt=now + timedelta(hours=2), starts_at__lte=now + timedelta(hours=24)):
        for r in EventRsvp.objects.filter(event=e).select_related("user")[:3000]:
            _notify(r.user, "Tomorrow: %s (%s)" % (e.title, timezone.localtime(e.starts_at).strftime("%d %b, %I:%M %p")), "/events#e%d" % e.id); n += 1
        Event.objects.filter(pk=e.pk).update(reminded_day=True)
    for e in Event.objects.filter(cancelled=False, reminded_hour=False, starts_at__gt=now, starts_at__lte=now + timedelta(minutes=75)):
        for r in EventRsvp.objects.filter(event=e).select_related("user")[:3000]:
            _notify(r.user, "Starting soon: %s at %s" % (e.title, timezone.localtime(e.starts_at).strftime("%I:%M %p")), "/events#e%d" % e.id); n += 1
        Event.objects.filter(pk=e.pk).update(reminded_hour=True, reminded_day=True)
    return n


# ---------------------------------------------------------------- articles and newsletter
def _art_out(a, u, full=False):
    d = {"id": a.id, "title": a.title, "by": _who(a.author), "cover": _media(a.cover), "when": a.created_at.isoformat(), "views": a.views,
         "excerpt": re.sub(r"\s+", " ", a.body)[:220], "mine": u.is_authenticated and u.pk == a.author_id, "link": SITE + "/articles#a%d" % a.id,
         "minutes": max(1, len(a.body.split()) // 200)}
    if full:
        d["body"] = a.body
        d["subscribers"] = Subscription.objects.filter(writer=a.author).count()
        d["subscribed"] = u.is_authenticated and Subscription.objects.filter(reader=u, writer=a.author).exists()
    return d


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def articles(request):
    u = request.user
    if request.method == "GET":
        qs = Article.objects.filter(hidden=False).select_related("author")
        by = request.GET.get("by")
        if by:
            w = _profile_user(by)
            qs = qs.filter(author=w) if w else qs.none()
        elif request.GET.get("subs") and u.is_authenticated:
            qs = qs.filter(author_id__in=Subscription.objects.filter(reader=u).values_list("writer_id", flat=True))
        if u.is_authenticated:
            from .privacy import blocked_ids
            b = blocked_ids(u)
            if b:
                qs = qs.exclude(author_id__in=b)
        return Response({"articles": [_art_out(a, u) for a in qs[:50]]})
    if not u.is_authenticated:
        return _err("Sign in first.", 403)
    if not _email_ok(u):
        return _err("Verify your email first.", 403)
    title, body = _txt(request.data.get("title"), 160), str(request.data.get("body") or "").strip()[:40000]
    if len(title) < 5:
        return _err("Give your article a title.")
    if len(body.split()) < 80:
        return _err("An article needs at least 80 words. For something shorter, write a post.")
    if Article.objects.filter(author=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= 3:
        return _err("You can publish 3 articles a day.")
    cover = ""
    if request.FILES.get("cover"):
        try:
            cover = _save_cover(request.FILES["cover"], "articles", u.pk)
        except ValueError as ex:
            return _err(str(ex))
    a = Article.objects.create(author=u, title=title, body=body, cover=cover)
    try:                                     # a post on XpertConnect, so the article shows in the feed
        from feed.models import Post
        Post.objects.create(author=u, body="\U0001F4F0 New article: %s\n\n%s…\n\nRead it: %s/articles#a%d" % (title, re.sub(r"\s+", " ", body)[:200], SITE, a.id),
                            images=[cover] if cover else [], visibility="public")
    except Exception:
        pass
    for s in Subscription.objects.filter(writer=u).select_related("reader")[:5000]:
        _notify(s.reader, "\U0001F4F0 %s published: %s" % (_name(u), title), "/articles#a%d" % a.id)
    return Response(_art_out(a, u, True))


@api_view(["GET"])
@permission_classes([AllowAny])
def article(request, aid):
    a = Article.objects.filter(pk=aid).select_related("author").first()
    u = request.user
    if not a or (a.hidden and not (_staff(u) or (u.is_authenticated and u.pk == a.author_id))) or (u.is_authenticated and _blocked(u.pk, a.author_id)):
        return _err("Article not found.", 404)
    Article.objects.filter(pk=a.pk).update(views=F("views") + 1)
    return Response(_art_out(a, u, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def article_act(request, aid, act):
    u = request.user
    a = Article.objects.filter(pk=aid).first()
    if not a:
        return _err("Not found.", 404)
    if act == "edit" and u.pk == a.author_id:
        t, b = _txt(request.data.get("title"), 160), str(request.data.get("body") or "").strip()[:40000]
        if len(t) < 5 or len(b.split()) < 80:
            return _err("Keep a title and at least 80 words.")
        a.title, a.body = t, b; a.save(update_fields=["title", "body", "updated_at"])
        return Response(_art_out(a, u, True))
    if act == "delete" and (u.pk == a.author_id or _staff(u)):
        a.delete(); return Response({"deleted": True})
    if act in ("hide", "unhide") and _staff(u):
        a.hidden = act == "hide"; a.save(update_fields=["hidden"]); return Response(_art_out(a, u))
    return _err("Not allowed.", 403)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def subscribe(request):
    u = request.user
    w = _profile_user(request.GET.get("slug") if request.method == "GET" else request.data.get("slug"))
    if not w:
        return _err("Not found.", 404)
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in first.", 403)
        if w.pk == u.pk:
            return _err("That is you.")
        if str(request.data.get("on")).lower() in ("true", "1"):
            _, made = Subscription.objects.get_or_create(reader=u, writer=w)
            if made:
                _notify(w, "%s subscribed to your newsletter." % _name(u), "/articles")
        else:
            Subscription.objects.filter(reader=u, writer=w).delete()
    return Response({"on": u.is_authenticated and Subscription.objects.filter(reader=u, writer=w).exists(),
                     "count": Subscription.objects.filter(writer=w).count(), "articles": Article.objects.filter(author=w, hidden=False).count(),
                     "me": u.is_authenticated and u.pk == w.pk})
