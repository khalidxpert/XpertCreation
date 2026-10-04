"""Afsanay: members write and publish their own stories, qist by qist. Own writing only."""
import importlib
from datetime import timedelta

from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Afsana, Bookmark, Comment, Follow, Like, Qist, Report

PER_DAY_NEW, PER_DAY_QIST, MAX_BODY = 3, 10, 30000


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _name(u):
    return ((getattr(u, "full_name", "") or "").strip() or getattr(u, "username", "") or "Writer") if u else "Writer"


def _notify(user, text, link):
    for mod in ("notifications.utils", "notifications.views", "notifications.models", "notifications"):
        try:
            f = getattr(importlib.import_module(mod), "notify", None)
            if callable(f):
                f(user, "afsana", text, link); return
        except Exception:
            continue


def _card(a, n_qists=None):
    return {"id": a.id, "title": a.title, "writer": _name(a.author), "writer_id": a.author_id, "category": a.category, "lang": a.lang,
            "summary": a.summary, "qists": n_qists if n_qists is not None else a.qists.count(), "likes": a.likes, "views": a.views,
            "complete": a.complete, "updated": a.updated_at.isoformat()}


def _visible(u):
    qs = Afsana.objects.select_related("author")
    return qs if _staff(u) else qs.filter(Q(hidden=False) | Q(author_id=getattr(u, "pk", 0)))


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def afsanay(request):
    u = request.user
    if request.method == "GET":
        qs = _visible(u).filter(hidden=False).annotate(nq=Count("qists")).filter(nq__gt=0)
        g = request.GET
        if g.get("cat") in dict(Afsana.CATS): qs = qs.filter(category=g["cat"])
        if g.get("lang") in ("ur", "en"): qs = qs.filter(lang=g["lang"])
        if g.get("writer", "").isdigit(): qs = qs.filter(author_id=int(g["writer"]))
        if g.get("q"): qs = qs.filter(Q(title__icontains=g["q"][:60]) | Q(summary__icontains=g["q"][:60]))
        if g.get("mine") and u.is_authenticated: qs = _visible(u).filter(author=u).annotate(nq=Count("qists"))
        if g.get("saved") and u.is_authenticated: qs = qs.filter(id__in=Bookmark.objects.filter(user=u).values("afsana_id"))
        qs = qs.order_by("-likes", "-views") if g.get("sort") == "top" else qs.order_by("-updated_at")
        return Response({"afsanay": [_card(a, a.nq) for a in qs[:60]], "cats": [{"key": k, "name": n} for k, n in Afsana.CATS]})
    if not u.is_authenticated:
        return Response({"detail": "Sign in to write."}, status=401)
    d = request.data
    title, body = str(d.get("title") or "").strip()[:120], str(d.get("body") or "").strip()
    if len(title) < 3 or len(body) < 200:
        return Response({"detail": "Add a title and at least 200 characters of your story."}, status=400)
    if Afsana.objects.filter(author=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= PER_DAY_NEW:
        return Response({"detail": "You can start up to %d new stories a day." % PER_DAY_NEW}, status=429)
    if not d.get("own"):
        return Response({"detail": "Please confirm this is your own writing."}, status=400)
    a = Afsana.objects.create(author=u, title=title, category=d.get("category") if d.get("category") in dict(Afsana.CATS) else "family",
                              lang="en" if d.get("lang") == "en" else "ur", summary=str(d.get("summary") or "").strip()[:300])
    Qist.objects.create(afsana=a, n=1, title=str(d.get("qist_title") or "").strip()[:120], body=body[:MAX_BODY])
    for f in Follow.objects.filter(writer=u).select_related("follower")[:500]:
        _notify(f.follower, "%s published a new story: %s" % (_name(u), title), "/afsanay?id=%d" % a.id)
    return Response(_card(a, 1), status=201)


@api_view(["GET", "DELETE", "POST"])
@permission_classes([AllowAny])
def afsana(request, pk):
    u = request.user; a = _visible(u).filter(pk=pk).first()
    if not a:
        return Response({"detail": "Story not found."}, status=404)
    if request.method == "GET":
        out = _card(a); out["list"] = [{"n": q.n, "title": q.title, "date": q.created_at.isoformat()} for q in a.qists.order_by("n")]
        out["mine"] = u.is_authenticated and a.author_id == u.pk; out["staff"] = _staff(u); out["hidden"] = a.hidden
        if u.is_authenticated:
            out.update(liked=Like.objects.filter(user=u, afsana=a).exists(), saved=Bookmark.objects.filter(user=u, afsana=a).exists(),
                       following=Follow.objects.filter(follower=u, writer=a.author).exists())
        out["comments"] = [{"id": c.id, "who": _name(c.user), "body": c.body, "date": c.created_at.isoformat()} for c in a.comments.filter(hidden=False).select_related("user").order_by("-id")[:50]]
        return Response(out)
    if not u.is_authenticated or not (a.author_id == u.pk or _staff(u)):
        return Response({"detail": "Only the writer can do that."}, status=403)
    if request.method == "DELETE":
        a.delete(); return Response({"deleted": True})
    if "complete" in request.data: a.complete = bool(request.data["complete"])
    if "hidden" in request.data and _staff(u): a.hidden = bool(request.data["hidden"])
    if request.data.get("summary") is not None: a.summary = str(request.data["summary"])[:300]
    a.save(); return Response(_card(a))


@api_view(["GET"])
@permission_classes([AllowAny])
def qist(request, pk, n):
    a = _visible(request.user).filter(pk=pk).first(); q = a and a.qists.filter(n=n).first()
    if not q:
        return Response({"detail": "Not found."}, status=404)
    Afsana.objects.filter(pk=a.pk).update(views=F("views") + 1)
    last = a.qists.order_by("-n").values_list("n", flat=True).first()
    return Response({"story": a.title, "id": a.id, "lang": a.lang, "writer": _name(a.author), "n": q.n, "title": q.title, "body": q.body,
                     "prev": q.n - 1 if q.n > 1 else None, "next": q.n + 1 if q.n < last else None, "complete": a.complete})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_qist(request, pk):
    u = request.user; a = Afsana.objects.filter(pk=pk, author=u).first()
    if not a:
        return Response({"detail": "Only the writer can add a qist."}, status=403)
    body = str(request.data.get("body") or "").strip()
    if len(body) < 200:
        return Response({"detail": "A qist needs at least 200 characters."}, status=400)
    if Qist.objects.filter(afsana__author=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= PER_DAY_QIST:
        return Response({"detail": "You can publish up to %d qists a day." % PER_DAY_QIST}, status=429)
    n = (a.qists.order_by("-n").values_list("n", flat=True).first() or 0) + 1
    Qist.objects.create(afsana=a, n=n, title=str(request.data.get("title") or "").strip()[:120], body=body[:MAX_BODY])
    a.complete = bool(request.data.get("complete")); a.save()
    who = set(Bookmark.objects.filter(afsana=a).values_list("user_id", flat=True)) | set(Follow.objects.filter(writer=u).values_list("follower_id", flat=True))
    from django.contrib.auth import get_user_model
    for r in get_user_model().objects.filter(pk__in=list(who)[:1000]).exclude(pk=u.pk):
        _notify(r, "New qist %d of \u201c%s\u201d by %s" % (n, a.title, _name(u)), "/afsanay?id=%d&q=%d" % (a.id, n))
    return Response({"n": n}, status=201)


def _toggle(model, **kw):
    o = model.objects.filter(**kw).first()
    if o:
        o.delete(); return False
    model.objects.create(**kw); return True


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def act(request, pk, what):
    u = request.user; a = Afsana.objects.filter(pk=pk, hidden=False).first()
    if not a:
        return Response({"detail": "Story not found."}, status=404)
    if what == "like":
        on = _toggle(Like, user=u, afsana=a); Afsana.objects.filter(pk=pk).update(likes=F("likes") + (1 if on else -1))
        return Response({"liked": on})
    if what == "save":
        return Response({"saved": _toggle(Bookmark, user=u, afsana=a)})
    if what == "follow":
        if a.author_id == u.pk:
            return Response({"detail": "That is you."}, status=400)
        return Response({"following": _toggle(Follow, follower=u, writer=a.author)})
    if what == "comment":
        body = str(request.data.get("body") or "").strip()[:1000]
        if len(body) < 2:
            return Response({"detail": "Write a comment."}, status=400)
        if Comment.objects.filter(user=u, created_at__gte=timezone.now() - timedelta(minutes=10)).count() >= 10:
            return Response({"detail": "Slow down a little."}, status=429)
        c = Comment.objects.create(afsana=a, user=u, body=body)
        if a.author_id != u.pk:
            _notify(a.author, "%s commented on \u201c%s\u201d" % (_name(u), a.title), "/afsanay?id=%d" % a.id)
        return Response({"id": c.id}, status=201)
    if what == "report":
        Report.objects.get_or_create(afsana=a, user=u, defaults={"reason": str(request.data.get("reason") or "")[:300]})
        n = Report.objects.filter(afsana=a).count()
        if n >= 5:
            a.hidden = True; a.save(update_fields=["hidden"])
        return Response({"reported": True})
    return Response({"detail": "Unknown action."}, status=400)
