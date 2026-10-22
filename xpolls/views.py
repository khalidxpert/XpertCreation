"""XpertChat polls - /api/polls/...
POST  ""            {thread|group, question, options: [...], multi}  make a poll; then the page sends "[poll:<id>] ..." as a message
GET   <id>/         results (anyone in that chat or group)
POST  <id>/vote/    {option}  tap again to take the vote back (one choice unless multi)
POST  <id>/close/   the person who made it stops the voting
"""
from django.core.cache import cache
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.models import ChatThread, GroupMember

from .models import Poll, PollVote


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _can(kind, ref, u):
    if kind == "t":
        t = ChatThread.objects.filter(pk=ref).first()
        return bool(t and t.has(u))
    return GroupMember.objects.filter(group_id=ref, user=u).exists()


def _out(p, u):
    counts = dict(p.votes.values_list("option").annotate(n=Count("id")))
    mine = set(p.votes.filter(user=u).values_list("option", flat=True))
    voters = p.votes.values("user").distinct().count()
    return {"id": p.id, "question": p.question, "multi": p.multi, "closed": p.closed, "mine_author": p.author_id == u.id, "voters": voters,
            "options": [{"text": t, "count": counts.get(i, 0), "mine": i in mine} for i, t in enumerate(p.options)]}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create(request):
    u, d = request.user, request.data
    kind, ref = ("t", d.get("thread")) if d.get("thread") else ("g", d.get("group"))
    try:
        ref = int(ref)
    except (TypeError, ValueError):
        return _err("Where should the poll go?")
    if not _can(kind, ref, u):
        return _err("Chat not found.", 404)
    if not cache.add("xcpoll:%d" % u.pk, 1, 5):
        return _err("Please wait a moment.", 429)
    q = " ".join(str(d.get("question") or "").split())[:200]
    opts = [" ".join(str(o).split())[:80] for o in (d.get("options") or []) if str(o).strip()][:12]
    if len(q) < 2:
        return _err("Write the question.")
    if len(opts) < 2:
        return _err("Add at least two options.")
    if len(set(o.lower() for o in opts)) != len(opts):
        return _err("Two options are the same.")
    p = Poll.objects.create(kind=kind, ref_id=ref, author=u, question=q, options=opts, multi=bool(d.get("multi")))
    return Response(_out(p, u))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail(request, pk):
    p = Poll.objects.filter(pk=pk).first()
    if not p or not _can(p.kind, p.ref_id, request.user):
        return _err("Poll not found.", 404)
    return Response(_out(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vote(request, pk):
    u = request.user
    p = Poll.objects.filter(pk=pk).first()
    if not p or not _can(p.kind, p.ref_id, u):
        return _err("Poll not found.", 404)
    if p.closed:
        return _err("Voting has ended.")
    try:
        i = int(request.data.get("option"))
    except (TypeError, ValueError):
        return _err("Pick an option.")
    if i < 0 or i >= len(p.options):
        return _err("Pick an option.")
    had = PollVote.objects.filter(poll=p, user=u, option=i)
    if had.exists():
        had.delete()
    else:
        if not p.multi:
            PollVote.objects.filter(poll=p, user=u).delete()
        PollVote.objects.create(poll=p, user=u, option=i)
    return Response(_out(p, u))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def close(request, pk):
    p = Poll.objects.filter(pk=pk, author=request.user).first()
    if not p:
        return _err("Only the person who made the poll can end it.", 403)
    p.closed = True
    p.save(update_fields=["closed"])
    return Response(_out(p, request.user))
