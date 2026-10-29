"""Lesson Q&A for XpertAcademy - /api/learnx/...
qa/?course=excel&lesson=3          GET   questions with their answers (anyone can read)
qa/                                POST  {course, lesson, body, parent?}  ask, or answer a question (signed in)
qa/counts/?course=excel            GET   {lesson: number of questions}
qa/<id>/delete/                    POST  your own post, or any post if you are staff
qa/<id>/helpful/                   POST  the person who asked marks an answer as helpful (again to undo)
"""
import re
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import LessonQA

SLUG = re.compile(r"^[a-z0-9_-]{1,40}$")
KEY = re.compile(r"^[A-Za-z0-9_.:-]{1,60}$")


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _name(u):
    return (getattr(u, "full_name", "") or u.get_full_name() or u.username or "Member").strip()


def _slug(u):
    try:
        from network.models import ProProfile
        return ProProfile.objects.filter(user=u).values_list("slug", flat=True).first() or ""
    except Exception:
        return ""


def _notify(user, text, link):
    try:
        from notifications.views import notify
        notify(user, "academy_qa", text, link)
    except Exception:
        pass


def _row(q, me, slugs):
    return {"id": q.id, "body": q.body, "name": _name(q.user), "slug": slugs.get(q.user_id, ""), "uid": q.user_id,
            "mine": bool(me and me.is_authenticated and q.user_id == me.id), "staff": _staff(q.user),
            "helpful": q.helpful, "at": q.created.isoformat()}


def _err(m, c=400):
    return Response({"detail": m}, status=c)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def qa(request):
    u = request.user
    if request.method == "GET":
        c, l = request.GET.get("course", ""), request.GET.get("lesson", "")
        if not SLUG.match(c) or not KEY.match(l):
            return _err("Unknown lesson.")
        rows = list(LessonQA.objects.filter(course=c, lesson=l, hidden=False).select_related("user"))
        slugs = {}
        try:
            from network.models import ProProfile
            from network.views import _get_or_make
            _ids = {r.user_id for r in rows}
            slugs = dict(ProProfile.objects.filter(user_id__in=_ids).values_list("user_id", "slug"))
            _missing = [uid for uid in _ids if not slugs.get(uid)]
            if _missing:
                from django.contrib.auth import get_user_model
                for _us in get_user_model().objects.filter(pk__in=_missing):
                    try:
                        slugs[_us.pk] = _get_or_make(_us).slug
                    except Exception:
                        pass
        except Exception:
            pass
        qs = [r for r in rows if r.parent_id is None]
        kids = {}
        for r in rows:
            if r.parent_id:
                kids.setdefault(r.parent_id, []).append(r)
        out = []
        for q in reversed(qs):          # newest question first, answers oldest first
            d = _row(q, u, slugs)
            d["answers"] = [_row(a, u, slugs) for a in sorted(kids.get(q.id, []), key=lambda a: (not a.helpful, a.created))]
            out.append(d)
        return Response({"questions": out, "me": bool(u.is_authenticated), "staff": _staff(u)})
    if not u.is_authenticated:
        return _err("Sign in to ask or answer.", 401)
    d = request.data
    c, l = str(d.get("course") or ""), str(d.get("lesson") or "")
    body = re.sub(r"\s+\n", "\n", str(d.get("body") or "")).strip()
    if not SLUG.match(c) or not KEY.match(l):
        return _err("Unknown lesson.")
    if len(body) < 5:
        return _err("Write a little more (at least 5 letters).")
    if len(body) > 1000:
        return _err("Please keep it under 1000 letters.")
    if not cache.add("xclqa:%d" % u.pk, 1, 15):
        return _err("Please wait a few seconds before posting again.", 429)
    if LessonQA.objects.filter(user=u, created__gte=timezone.now() - timedelta(days=1)).count() >= 40:
        return _err("That is a lot for one day. Please try again tomorrow.", 429)
    parent = None
    if d.get("parent"):
        try:
            parent = LessonQA.objects.select_related("user").get(pk=int(d.get("parent")), parent__isnull=True, hidden=False)
        except (LessonQA.DoesNotExist, TypeError, ValueError):
            return _err("That question is gone.", 404)
        c, l = parent.course, parent.lesson
    q = LessonQA.objects.create(course=c, lesson=l, user=u, parent=parent, body=body)
    link = "/academy/?c=%s&l=%s#qa" % (c, l)
    if parent:
        if parent.user_id != u.id:
            _notify(parent.user, "%s answered your question in the %s course: %s" % (_name(u), c, body[:60]), link)
        seen = {parent.user_id, u.id}
        for a in parent.answers.exclude(user_id__in=seen).select_related("user")[:30]:
            if a.user_id not in seen:
                seen.add(a.user_id)
                _notify(a.user, "New answer on a question you answered (%s course)" % c, link)
    else:
        try:
            from notifications.views import notify_admins
            notify_admins("academy_qa", "%s asked a question in the %s course: %s" % (_name(u), c, body[:60]), link)
        except Exception:
            pass
    return Response(_row(q, u, {u.id: _slug(u)}) | {"answers": [], "parent": parent.id if parent else None})


@api_view(["GET"])
@permission_classes([AllowAny])
def qa_counts(request):
    c = request.GET.get("course", "")
    if not SLUG.match(c):
        return _err("Unknown course.")
    rows = LessonQA.objects.filter(course=c, parent__isnull=True, hidden=False).values("lesson").annotate(n=Count("id"))
    return Response({r["lesson"]: r["n"] for r in rows})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def qa_delete(request, pk):
    q = LessonQA.objects.filter(pk=pk, hidden=False).first()
    if not q:
        return _err("Not found.", 404)
    if q.user_id != request.user.id and not _staff(request.user):
        return _err("You can delete only your own posts.", 403)
    q.hidden = True
    q.save(update_fields=["hidden"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def qa_helpful(request, pk):
    a = LessonQA.objects.select_related("parent").filter(pk=pk, hidden=False, parent__isnull=False).first()
    if not a:
        return _err("Not found.", 404)
    if a.parent.user_id != request.user.id and not _staff(request.user):
        return _err("Only the person who asked can mark an answer helpful.", 403)
    a.helpful = not a.helpful
    a.save(update_fields=["helpful"])
    if a.helpful and a.user_id != request.user.id:
        _notify(a.user, "Your answer was marked helpful ✔ (%s course)" % a.course, "/academy/?c=%s&l=%s#qa" % (a.course, a.lesson))
    return Response({"helpful": a.helpful})
