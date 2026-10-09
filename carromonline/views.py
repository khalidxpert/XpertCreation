"""Online carrom rooms (2 players, or 4 players in two teams). Players must be signed in.
Shots are played on the shooter's phone; the result is saved here and replayed on the other phones."""
import json
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Room

ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SKIP_AFTER = 75          # seconds without a shot before the others may skip that turn


def _name(u):
    n = (getattr(u, "full_name", "") or "").strip()
    if not n and hasattr(u, "get_full_name"):
        n = (u.get_full_name() or "").strip()
    return (n or u.username)[:40]


def _seat(room, u):
    for p in room.players:
        if p.get("id") == u.id:
            return p.get("seat")
    return None


def _out(room, u):
    return {"code": room.code, "size": room.size, "players": room.players, "status": room.status, "state": room.state,
            "shot": room.shot, "version": room.version, "host": room.host_id == u.id, "seat": _seat(room, u),
            "ago": int((timezone.now() - room.updated_at).total_seconds())}


def _bump(room):
    room.version += 1
    room.save()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create(request):
    size = 4 if str(request.data.get("size")) == "4" else 2
    Room.objects.filter(updated_at__lt=timezone.now() - timedelta(days=2)).delete()
    for _ in range(20):
        code = "".join(random.choice(ALPHA) for _ in range(5))
        if not Room.objects.filter(code=code).exists():
            break
    r = Room.objects.create(code=code, size=size, host=request.user, players=[{"id": request.user.id, "name": _name(request.user), "seat": 0}])
    return Response(_out(r, request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def room(request, code):
    r = Room.objects.filter(code=code.upper()).first()
    if not r:
        return Response({"detail": "No table with that code."}, status=404)
    v = request.GET.get("v")
    if v is not None and str(r.version) == v:
        return Response({"same": True, "version": r.version, "ago": int((timezone.now() - r.updated_at).total_seconds())})
    return Response(_out(r, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join(request, code):
    with transaction.atomic():
        r = Room.objects.select_for_update().filter(code=code.upper()).first()
        if not r:
            return Response({"detail": "No table with that code."}, status=404)
        if _seat(r, request.user) is None:
            if r.status != "wait" or len(r.players) >= r.size:
                return Response({"detail": "This table is full."}, status=409)
            taken = {p["seat"] for p in r.players}
            seat = min(s for s in range(r.size) if s not in taken)
            r.players = r.players + [{"id": request.user.id, "name": _name(request.user), "seat": seat}]
            _bump(r)
    return Response(_out(r, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave(request, code):
    with transaction.atomic():
        r = Room.objects.select_for_update().filter(code=code.upper()).first()
        if r and r.status == "wait" and r.host_id != request.user.id:
            r.players = [p for p in r.players if p.get("id") != request.user.id]
            _bump(r)
    return Response({"ok": True})


def _state_ok(s):
    return isinstance(s, dict) and isinstance(s.get("ps"), list) and isinstance(s.get("st"), dict) and len(json.dumps(s)) < 60000


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start(request, code):
    """Host only: deal a new board (first board when the table is full, or the next board after one ends)."""
    with transaction.atomic():
        r = Room.objects.select_for_update().filter(code=code.upper()).first()
        if not r or r.host_id != request.user.id:
            return Response({"detail": "Only the host can start."}, status=403)
        if len(r.players) < r.size:
            return Response({"detail": "Wait until every seat is taken."}, status=409)
        s = request.data.get("state")
        if not _state_ok(s):
            return Response({"detail": "Bad board."}, status=400)
        r.state, r.shot, r.status = s, None, "play"
        _bump(r)
    return Response(_out(r, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def shot(request, code):
    with transaction.atomic():
        r = Room.objects.select_for_update().filter(code=code.upper()).first()
        if not r or r.status != "play" or not r.state:
            return Response({"detail": "The game is not running."}, status=409)
        me = _seat(r, request.user)
        if me is None or me != r.state.get("seat"):
            return Response({"detail": "It is not your turn."}, status=403)
        if str(request.data.get("v")) != str(r.version):
            return Response({"detail": "The board changed. Updating…", "stale": True}, status=409)
        end, start_s, sh = request.data.get("end"), request.data.get("start"), request.data.get("shot")
        if not _state_ok(end) or not isinstance(start_s, list) or not isinstance(sh, dict):
            return Response({"detail": "Bad shot."}, status=400)
        r.state, r.shot = end, {"seat": me, "shot": sh, "start": start_s}
        if end.get("st", {}).get("over"):
            r.status = "over"
        _bump(r)
    return Response({"version": r.version})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def skip(request, code):
    """Anyone at the table may skip a player who has not shot for a while (left, or lost connection)."""
    with transaction.atomic():
        r = Room.objects.select_for_update().filter(code=code.upper()).first()
        if not r or r.status != "play" or not r.state or _seat(r, request.user) is None:
            return Response({"detail": "Nothing to skip."}, status=409)
        if (timezone.now() - r.updated_at).total_seconds() < SKIP_AFTER:
            return Response({"detail": "Give them a little longer."}, status=409)
        s = dict(r.state)
        seat = (int(s.get("seat", 0)) + 1) % r.size
        s["seat"] = seat
        st = dict(s.get("st") or {}); st["turn"] = seat % 2; s["st"] = st
        r.state, r.shot = s, None
        _bump(r)
    return Response(_out(r, request.user))
