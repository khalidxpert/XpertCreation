"""/api/xsocial/  - XpertConnect extras, part 2.
frames/?slugs=a,b        photo frames for these profiles (open = Open to work, hiring = Hiring)
frame/          GET/POST my frame
polls/          POST     add a poll to my new post  {post, options[], days}
polls/?ids=1,2  GET      polls on these posts (counts show after you vote, to the author, or when it ends)
polls/<post>/vote/ POST  {option}  (you can change your vote until it ends)
memories/       GET      my posts from this day in earlier years
celebrate/      GET      connections with a birthday today and work anniversaries this month
wish/           POST     {to, kind, text}  wish them (once a year each)
ambassadors/    GET      XpertCreation Brand Ambassadors (public), my application, and (team) applications waiting
ambassadors/apply/ POST  {city, why} - needs an XpertConnect profile and an approved ID check
ambassadors/team/<id>/<approve|reject|remove>/ POST  team only; approved = badge + blue tick"""
import re
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Ambassador, Frame, Poll, PollVote, Wish


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _ids(s, n=60):
    return [int(x) for x in str(s or "").split(",") if x.strip().isdigit()][:n]


def _name(u):
    return (getattr(u, "full_name", "") or getattr(u, "username", "") or "Member").strip()


def _avatar(u):
    try:
        from accounts.views import avatar_url
        return avatar_url(getattr(u, "avatar", "")) or ""
    except Exception:
        return ""


def _slug(u):
    p = getattr(u, "pro", None)
    try:
        return p.slug if p else ""
    except Exception:
        return ""


def _friends(u):
    """Ids of accepted connections."""
    try:
        from network.models import Connection
        rows = Connection.objects.filter(Q(from_user=u) | Q(to_user=u), state="accepted").values_list("from_user_id", "to_user_id")
        return {b if a == u.pk else a for a, b in rows}
    except Exception:
        return set()


def _can_see(post, u):
    if post.hidden:
        return False
    if post.visibility == "public":
        return True
    if not u.is_authenticated:
        return False
    if post.visibility == "members" or post.author_id == u.pk:
        return True
    return post.author_id in _friends(u)


# ---------------------------------------------------------------- frames
def _frame_of(p, fr):
    if fr and fr.kind == "hiring":
        return {"kind": "hiring", "text": fr.text or "Hiring"}
    if p and p.open_to_work:
        return {"kind": "open", "text": ("Open to work" + (": " + p.open_to if p.open_to else ""))[:120]}
    return None


@api_view(["GET"])
@permission_classes([AllowAny])
def frames(request):
    from network.models import ProProfile
    slugs = [s for s in str(request.GET.get("slugs") or "").split(",") if re.match(r"^[a-z0-9-]{1,60}$", s, re.I)][:80]
    out = {}
    amb = {}
    for p in ProProfile.objects.filter(slug__in=slugs).select_related("user"):
        f = _frame_of(p, Frame.objects.filter(user_id=p.user_id).first())
        if f:
            out[p.slug] = f
        a = Ambassador.objects.filter(user_id=p.user_id, active=True).first()
        if a:
            amb[p.slug] = a.title
    return Response({"frames": out, "ambassadors": amb})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def frame(request):
    from network.models import ProProfile
    u = request.user
    p = ProProfile.objects.filter(user=u).first()
    fr = Frame.objects.filter(user=u).first()
    if request.method == "POST":
        if not p:
            return _err("Create your XpertConnect profile first.", 403)
        kind, text = request.data.get("kind"), _txt(request.data.get("text"), 100)
        if kind not in ("", "open", "hiring"):
            return _err("Choose a frame.")
        fr = fr or Frame(user=u)
        fr.kind = "hiring" if kind == "hiring" else ""
        fr.text = text if kind == "hiring" else ""
        fr.save()
        upd = {"open_to_work": kind == "open"}
        if kind == "open":
            upd["open_to"] = text[:120] if text else p.open_to
        ProProfile.objects.filter(pk=p.pk).update(**upd)
        p.refresh_from_db()
    f = _frame_of(p, fr)
    return Response({"slug": p.slug if p else "", "kind": f["kind"] if f else "", "text": (fr.text if f and f["kind"] == "hiring" else (p.open_to if p else "")) if f else ""})


# ---------------------------------------------------------------- polls
def _poll_out(pl, u):
    votes = list(pl.votes.values_list("option", flat=True))
    mine = pl.votes.filter(user_id=u.pk).values_list("option", flat=True).first() if u.is_authenticated else None
    closed = pl.ends_at <= timezone.now()
    show = closed or mine is not None or (u.is_authenticated and u.pk == pl.post.author_id)
    return {"options": [{"t": t, "n": (votes.count(i) if show else None)} for i, t in enumerate(pl.options)], "total": len(votes),
            "mine": mine, "closed": closed, "ends": pl.ends_at.isoformat(), "show": show}


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def polls(request):
    u = request.user
    if request.method == "POST":
        if not u.is_authenticated:
            return _err("Sign in first.", 403)
        from feed.models import Post
        post = Post.objects.filter(pk=request.data.get("post") or 0, author=u).first()
        if not post:
            return _err("Post not found.", 404)
        if post.created_at < timezone.now() - timedelta(minutes=15):
            return _err("A poll can be added only right after posting.")
        if Poll.objects.filter(post=post).exists():
            return _err("This post already has a poll.")
        opts = [_txt(x, 80) for x in (request.data.get("options") or []) if _txt(x, 80)][:4]
        if len(opts) < 2 or len(set(o.lower() for o in opts)) != len(opts):
            return _err("Give 2 to 4 different choices.")
        days = request.data.get("days") if request.data.get("days") in (1, 3, 7, 14, "1", "3", "7", "14") else 7
        pl = Poll.objects.create(post=post, options=opts, ends_at=timezone.now() + timedelta(days=int(days)))
        return Response({"post": post.id, "poll": _poll_out(pl, u)})
    out = {}
    for pl in Poll.objects.filter(post_id__in=_ids(request.GET.get("ids"))).select_related("post"):
        if _can_see(pl.post, u):
            out[pl.post_id] = _poll_out(pl, u)
    return Response({"polls": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vote(request, pid):
    pl = Poll.objects.filter(post_id=pid).select_related("post").first()
    if not pl or not _can_see(pl.post, request.user):
        return _err("Poll not found.", 404)
    if pl.ends_at <= timezone.now():
        return _err("This poll has ended.")
    try:
        opt = int(request.data.get("option"))
    except (TypeError, ValueError):
        opt = -1
    if not 0 <= opt < len(pl.options):
        return _err("Choose one of the choices.")
    PollVote.objects.update_or_create(poll=pl, user=request.user, defaults={"option": opt})
    return Response({"post": pid, "poll": _poll_out(pl, request.user)})


# ---------------------------------------------------------------- memories and wishes
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def memories(request):
    from feed.models import Post
    now = timezone.localtime()
    rows = Post.objects.filter(author=request.user, hidden=False, created_at__month=now.month, created_at__day=now.day, created_at__year__lt=now.year).order_by("-created_at")[:5]
    return Response({"memories": [{"id": p.id, "years": now.year - p.created_at.year, "year": p.created_at.year, "body": p.body[:280],
                                   "image": ("/media/" + p.images[0]) if p.images else ""} for p in rows]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def celebrate(request):
    from django.contrib.auth import get_user_model
    u = request.user
    now = timezone.localtime()
    fr = _friends(u)
    out = []
    if fr:
        U = get_user_model()
        fields = {f.name for f in U._meta.get_fields()}
        if {"birth_day", "birth_month"} <= fields:
            q = U.objects.filter(pk__in=fr, is_active=True, birth_day=now.day, birth_month=now.month)
            if "show_birthday" in fields:
                q = q.filter(show_birthday=True)
            for x in q[:30]:
                out.append({"kind": "birthday", "id": x.pk, "name": _name(x), "avatar": _avatar(x), "slug": _slug(x), "text": "Birthday today \U0001F382"})
        try:
            from network.models import Experience
            for e in Experience.objects.filter(profile__user_id__in=fr, end_year__isnull=True, start_month=now.month, start_year__lt=now.year).select_related("profile__user")[:30]:
                x = e.profile.user; n = now.year - e.start_year
                out.append({"kind": "work", "id": x.pk, "name": _name(x), "avatar": _avatar(x), "slug": e.profile.slug,
                            "text": "%d year%s at %s" % (n, "" if n == 1 else "s", e.company or e.title)})
        except Exception:
            pass
    done = set(Wish.objects.filter(sender=u, year=now.year).values_list("to_id", "kind"))
    for x in out:
        x["wished"] = (x["id"], x["kind"]) in done
    return Response({"people": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def wish(request):
    u, now = request.user, timezone.localtime()
    kind = request.data.get("kind")
    try:
        to = int(request.data.get("to"))
    except (TypeError, ValueError):
        to = 0
    if kind not in ("birthday", "work") or to not in _friends(u):
        return _err("You can wish your connections only.", 403)
    from django.contrib.auth import get_user_model
    x = get_user_model().objects.filter(pk=to).first()
    text = _txt(request.data.get("text"), 200) or ("Happy birthday! \U0001F382" if kind == "birthday" else "Congratulations on your work anniversary! \U0001F389")
    w, made = Wish.objects.get_or_create(sender=u, to=x, kind=kind, year=now.year, defaults={"text": text})
    if made:
        try:
            from notifications.views import notify
            notify(x, "social", "%s %s: %s" % (_name(u), "wished you a happy birthday" if kind == "birthday" else "congratulated you on your work anniversary", text),
                   "/in/" + _slug(u) if _slug(u) else "/feed")
        except Exception:
            pass
    return Response({"ok": True, "wished": True})


# ---------------------------------------------------------------- brand ambassadors
def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _amb_out(a, full=False):
    u = a.user; p = getattr(u, "pro", None)
    d = {"id": a.id, "name": _name(u), "slug": _slug(u), "avatar": _avatar(u), "title": a.title, "city": a.city or (getattr(p, "city", "") if p else ""),
         "headline": getattr(p, "headline", "") if p else "", "status": a.status}
    if full:
        d.update({"why": a.why, "reason": a.reason, "email": u.email, "when": a.added_at.isoformat()})
    return d


def _kyc_ok(u):
    try:
        from companies.models import PersonKyc
        return PersonKyc.objects.filter(user_id=u.pk, status="approved").exists()
    except Exception:
        return False


def set_tick(u, on):
    """Approved ambassadors get the blue tick free. When removed, the tick goes too unless they paid for it."""
    from network.models import ProProfile
    p = ProProfile.objects.filter(user=u).first()
    if not p:
        return
    if not on:
        try:
            from kyctick.logic import tick_paid
            if tick_paid(u):
                return
        except Exception:
            pass
    upd = {"verified": on}
    if "verified_at" in {f.name for f in p._meta.get_fields()}:
        upd["verified_at"] = timezone.now() if on else None
    ProProfile.objects.filter(pk=p.pk).update(**upd)


def _notify(u, text, link="/ambassadors"):
    try:
        from notifications.views import notify
        notify(u, "social", text, link)
    except Exception:
        pass


@api_view(["GET"])
@permission_classes([AllowAny])
def ambassadors(request):
    u = request.user
    out = {"ambassadors": [_amb_out(a) for a in Ambassador.objects.filter(active=True).select_related("user")], "staff": _staff(u), "mine": None, "can_apply": False}
    if u.is_authenticated:
        m = Ambassador.objects.filter(user=u).first()
        out["mine"] = _amb_out(m, True) if m else None
        out["kyc"] = _kyc_ok(u)
        out["has_profile"] = bool(_slug(u))
        out["can_apply"] = out["kyc"] and out["has_profile"] and (not m or m.status in ("rejected", "removed"))
    if _staff(u):
        out["applications"] = [_amb_out(a, True) for a in Ambassador.objects.filter(status="pending").select_related("user").order_by("added_at")]
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def amb_apply(request):
    u = request.user
    if not _slug(u):
        return _err("Create your XpertConnect profile first.", 403)
    if not _kyc_ok(u):
        return _err("Verify your ID first on /get-verified. Ambassadors get the blue tick, so the ID check comes first.", 403)
    a = Ambassador.objects.filter(user=u).first()
    if a and a.status in ("pending", "approved"):
        return _err("You already applied." if a.status == "pending" else "You are already an ambassador.")
    why, city = _txt(request.data.get("why"), 800), _txt(request.data.get("city"), 60)
    if len(why) < 30:
        return _err("Tell us in a few lines why you want to be an ambassador and how you will help people (30+ letters).")
    if not city:
        return _err("Write your city.")
    a = a or Ambassador(user=u)
    a.status, a.active, a.why, a.city, a.reason = "pending", False, why, city, ""
    a.save()
    try:
        from notifications.views import notify_admins
        notify_admins("social", "New Brand Ambassador application from %s (%s)." % (_name(u), city), "/ambassadors")
    except Exception:
        pass
    return Response(_amb_out(a, True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def amb_team(request, aid, act):
    if not _staff(request.user):
        return _err("Team only.", 403)
    a = Ambassador.objects.filter(pk=aid).select_related("user").first()
    if not a or act not in ("approve", "reject", "remove"):
        return _err("Not found.", 404)
    if act == "approve":
        a.status, a.active, a.reason = "approved", True, ""
        t = _txt(request.data.get("title"), 60)
        if t:
            a.title = t
        a.save(); set_tick(a.user, True)
        _notify(a.user, "\u2B50 Welcome! You are now an XpertCreation %s. Your blue tick is on." % a.title)
    elif act == "reject":
        reason = _txt(request.data.get("reason"), 200)
        if len(reason) < 4:
            return _err("Write the reason (the member sees it).")
        a.status, a.active, a.reason = "rejected", False, reason; a.save()
        _notify(a.user, "Your Brand Ambassador application was not approved: %s" % reason)
    else:
        was = a.active
        a.status, a.active = "removed", False; a.save()
        if was:
            set_tick(a.user, False)
    return Response(_amb_out(a, True))
