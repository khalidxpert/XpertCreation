import re
import secrets
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import lk
from .models import Live

MAX_ACTIVE = 3              # lives at the same time on this server (2 cores)
STALE = 75                  # seconds without a beat from the host = the live is over
NOTIFY_MAX = 500


def _err(m, c=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": m}, status=c)


def _name(u):
    return (getattr(u, "full_name", "") or "").strip() or u.get_username() or "Member"


def _who(u):
    av, slug = "", ""
    try:
        from accounts.views import avatar_url
        av = avatar_url(u.avatar) if getattr(u, "avatar", "") else ""
    except Exception:
        pass
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).only("slug").first()
        slug = p.slug if p else ""
    except Exception:
        pass
    return {"id": u.pk, "name": _name(u), "avatar": av, "slug": slug}


def _tidy():
    cut = timezone.now() - timedelta(seconds=STALE)
    for lv in Live.objects.filter(status="live"):
        if (lv.beat_at or lv.started_at) < cut:
            _end(lv)


def _end(lv):
    lv.status = "ended"; lv.ended_at = timezone.now(); lv.viewers = 0
    lv.save(update_fields=["status", "ended_at", "viewers"])
    lk.call("DeleteRoom", lv.room, {"room": lv.room})


def shape(lv, me=None):
    secs = int(((lv.ended_at or timezone.now()) - lv.started_at).total_seconds())
    return {"id": lv.id, "title": lv.title, "host": _who(lv.host), "status": lv.status, "started": lv.started_at.isoformat(),
            "seconds": secs, "viewers": lv.viewers, "peak": lv.peak, "hearts": lv.hearts, "mine": bool(me and me.pk == lv.host_id),
            "url": "/live?id=%d" % lv.id}


@api_view(["GET"])
@permission_classes([AllowAny])
def lives(request):
    _tidy()
    me = request.user if request.user.is_authenticated else None
    out = [shape(lv, me) for lv in Live.objects.filter(status="live").select_related("host")[:30]]
    mine = None
    if me:
        m = Live.objects.filter(host=me, status="live").first()
        mine = m.id if m else None
    return Response({"lives": out, "mine": mine, "can_live": bool(me)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start(request):
    u = request.user
    _tidy()
    title = re.sub(r"[\x00-\x1f]", " ", str(request.data.get("title") or "")).strip()[:120] or (_name(u) + " is live")
    if cache.get("xlive:start:%d" % u.pk):
        return _err("One moment, please.", 429)
    cache.set("xlive:start:%d" % u.pk, 1, 8)
    old = Live.objects.filter(host=u, status="live").first()
    if old:
        lv = old
    else:
        if Live.objects.filter(status="live").count() >= MAX_ACTIVE:
            return _err("%d people are live right now, the most our server can carry. Try again in a few minutes." % MAX_ACTIVE, 503)
        lv = Live.objects.create(host=u, title=title, room="live-" + secrets.token_hex(8), beat_at=timezone.now())
        _tell_followers(u, lv)
    lv.beat_at = timezone.now(); lv.save(update_fields=["beat_at"])
    tok = lk.token("u%d" % u.pk, _name(u), lv.room, publish=True, data=True, metadata='{"host":1}')
    return Response({"live": shape(lv, u), "token": tok, "ws": lk.ws_url()}, status=201)


def _tell_followers(u, lv):
    try:
        from notifications.views import notify
    except Exception:
        return
    ids = set()
    try:
        from network.models import Connection, Follow
        ids.update(Follow.objects.filter(following=u).values_list("follower_id", flat=True)[:NOTIFY_MAX])
        ids.update(Connection.objects.filter(from_user=u, state="accepted").values_list("to_user_id", flat=True)[:NOTIFY_MAX])
        ids.update(Connection.objects.filter(to_user=u, state="accepted").values_list("from_user_id", flat=True)[:NOTIFY_MAX])
    except Exception:
        pass
    ids.discard(u.pk)
    from django.contrib.auth import get_user_model
    for f in get_user_model().objects.filter(pk__in=list(ids)[:NOTIFY_MAX]):
        try:
            notify(f, "live", "\U0001F534 %s is live now: %s" % (_name(u), lv.title), "/live?id=%d" % lv.id)
        except Exception:
            pass


@api_view(["GET"])
@permission_classes([AllowAny])
def watch(request, pk):
    _tidy()
    lv = Live.objects.filter(pk=pk).select_related("host").first()
    if not lv:
        return _err("This live was not found.", 404)
    me = request.user if request.user.is_authenticated else None
    out = {"live": shape(lv, me), "ws": lk.ws_url()}
    if lv.status != "live":
        return Response(out)
    if me:
        ident, name = "u%d" % me.pk, _name(me)
        if ident in (lv.blocked or []):
            return _err("The host removed you from this live.", 403)
        if me.pk == lv.host_id:
            out["token"] = lk.token(ident, name, lv.room, publish=True, metadata='{"host":1}')
            return Response(out)
        out["token"] = lk.token(ident, name, lv.room, publish=False, data=True)
        out["me"] = {"identity": ident, "name": name}
    else:
        key = request.session.get("xlive_guest") or ("g" + secrets.token_hex(5))
        request.session["xlive_guest"] = key
        out["token"] = lk.token(key, "Guest", lv.room, publish=False, data=False)
        out["me"] = {"identity": key, "name": "Guest", "guest": True}
    return Response(out)


def _mine(request, pk):
    return Live.objects.filter(pk=pk, host=request.user).first()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def beat(request, pk):
    lv = _mine(request, pk)
    if not lv or lv.status != "live":
        return _err("This live has ended.", 410)
    try:
        v = max(0, min(100000, int(request.data.get("viewers", 0))))
        h = max(0, min(10 ** 7, int(request.data.get("hearts", 0))))
    except (TypeError, ValueError):
        v, h = 0, 0
    lv.beat_at = timezone.now(); lv.viewers = v; lv.peak = max(lv.peak, v); lv.hearts = max(lv.hearts, h)
    lv.save(update_fields=["beat_at", "viewers", "peak", "hearts"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end(request, pk):
    lv = _mine(request, pk)
    if not lv:
        return _err("Not your live.", 404)
    if lv.status == "live":
        _end(lv)
    return Response({"live": shape(lv, request.user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stage(request, pk):
    """Host lets a viewer on screen (or takes them off)."""
    lv = _mine(request, pk)
    ident = str(request.data.get("identity") or "")
    if not lv or lv.status != "live" or not re.fullmatch(r"u\d+", ident) or ident == "u%d" % lv.host_id:
        return _err("Not possible.")
    on = bool(request.data.get("on"))
    r = lk.call("UpdateParticipant", lv.room, {"room": lv.room, "identity": ident,
                                                "permission": {"can_subscribe": True, "can_publish": on, "can_publish_data": True}})
    if r is None:
        return _err("Could not reach the live server. Try again.", 502)
    return Response({"ok": True, "on": on})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def block(request, pk):
    lv = _mine(request, pk)
    ident = str(request.data.get("identity") or "")
    if not lv or lv.status != "live" or not re.fullmatch(r"(u\d+|g[a-f0-9]{10})", ident) or ident == "u%d" % lv.host_id:
        return _err("Not possible.")
    b = list(lv.blocked or [])
    if ident not in b:
        b.append(ident); lv.blocked = b[-500:]; lv.save(update_fields=["blocked"])
    lk.call("RemoveParticipant", lv.room, {"room": lv.room, "identity": ident})
    return Response({"ok": True})
