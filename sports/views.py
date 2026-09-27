"""Sports pages read the saved copies (see feeds.py) - no provider is called per visitor, except a
cricket scorecard the first time someone opens a match (then it is saved too)."""
import re

from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import feeds
from .models import Prediction

PK = re.compile(r"\b(pakistan|pak|lahore qalandars|karachi kings|islamabad united|peshawar zalmi|quetta gladiators|multan sultans)\b", re.I)
PSL = re.compile(r"pakistan super league|\bpsl\b", re.I)


def _when(at):
    return timezone.localtime(at).strftime("%d %b, %H:%M") if at else ""


def _votes(sport, ids, user):
    if not ids:
        return {}
    out = {}
    for r in Prediction.objects.filter(sport=sport, match_id__in=[str(i) for i in ids]).values("match_id", "pick").annotate(n=Count("id")):
        out.setdefault(r["match_id"], {})[r["pick"]] = r["n"]
    mine = {}
    if user.is_authenticated:
        mine = dict(Prediction.objects.filter(user=user, sport=sport, match_id__in=[str(i) for i in ids]).values_list("match_id", "pick"))
    return {"votes": out, "mine": mine}


def _cricket_all():
    cur, at1 = feeds.get("cricket:current")
    lst, at2 = feeds.get("cricket:list")
    seen, allm = set(), []
    for m in (cur or {}).get("matches", []) + (lst or {}).get("matches", []):
        if m["id"] in seen:
            continue
        seen.add(m["id"]); m["pak"] = bool(PK.search(m["name"])); m["psl"] = bool(PSL.search(m["name"]))
        allm.append(m)
    return allm, max([a for a in (at1, at2) if a] or [None]) if (at1 or at2) else None


@api_view(["GET"])
@permission_classes([AllowAny])
def cricket(request):
    allm, at = _cricket_all()
    live = [m for m in allm if m["started"] and not m["ended"]]
    done = sorted([m for m in allm if m["ended"]], key=lambda m: m["date"], reverse=True)[:40]
    soon = sorted([m for m in allm if not m["started"]], key=lambda m: m["date"])[:40]
    key = lambda m: (not m["pak"], not m["psl"])
    live.sort(key=key)
    return Response({"live": live, "upcoming": soon, "results": done, "updated": _when(at),
                     "predictions": _votes("cricket", [m["id"] for m in live + soon], request.user)})


@api_view(["GET"])
@permission_classes([AllowAny])
def cricket_match(request, mid):
    if not re.match(r"^[0-9a-f-]{8,64}$", mid):
        return Response({"detail": "Not found."}, status=404)
    card = feeds.cricket_scorecard(mid)
    if not card:
        allm, _ = _cricket_all()
        card = next((m for m in allm if m["id"] == mid), None)
        if not card:
            return Response({"detail": "This match is not available."}, status=404)
        card = dict(card, innings=[], note="The full scorecard will appear once it is available.")
    card["predictions"] = _votes("cricket", [mid], request.user)
    return Response(card)


@api_view(["GET"])
@permission_classes([AllowAny])
def football(request):
    d, at = feeds.get("football:matches")
    ms = (d or {}).get("matches", [])
    code = str(request.GET.get("comp") or "").upper()[:6]
    if code:
        ms = [m for m in ms if m["comp"]["code"] == code]
    live = [m for m in ms if m["status"] in ("IN_PLAY", "PAUSED")]
    soon = sorted([m for m in ms if m["status"] in ("SCHEDULED", "TIMED")], key=lambda m: m["date"])[:60]
    done = sorted([m for m in ms if m["status"] == "FINISHED"], key=lambda m: m["date"], reverse=True)[:60]
    comps, _ = feeds.get("football:comps")
    return Response({"live": live, "upcoming": soon, "results": done, "updated": _when(at), "comps": (comps or {}).get("comps", []),
                     "predictions": _votes("football", [m["id"] for m in live + soon], request.user)})


@api_view(["GET"])
@permission_classes([AllowAny])
def football_table(request, code):
    d, at = feeds.get("football:table:" + code.upper()[:6])
    if not d:
        return Response({"detail": "This table will appear after the next update."}, status=404)
    return Response(dict(d, updated=_when(at)))


@api_view(["GET"])
@permission_classes([AllowAny])
def football_match(request, mid):
    d, _ = feeds.get("football:matches")
    m = next((x for x in (d or {}).get("matches", []) if x["id"] == mid), None)
    if not m:
        return Response({"detail": "This match is not in the current fixtures."}, status=404)
    return Response(dict(m, predictions=_votes("football", [mid], request.user)))


@api_view(["GET"])
@permission_classes([AllowAny])
def other(request, kind):
    d, at = feeds.get("other:" + re.sub(r"[^a-z0-9]", "", kind)[:12])
    if not d:
        return Response({"label": kind, "next": [], "past": [], "updated": ""})
    return Response(dict(d, updated=_when(at)))


@api_view(["GET"])
@permission_classes([AllowAny])
def home(request):
    allm, _ = _cricket_all()
    fm, _ = feeds.get("football:matches")
    return Response({"cricket_live": [m for m in allm if m["started"] and not m["ended"]][:6],
                     "football_live": [m for m in (fm or {}).get("matches", []) if m["status"] in ("IN_PLAY", "PAUSED")][:6]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def predict(request):
    """body: {sport: 'cricket'|'football', match_id, pick} - one pick per member per match, changeable until it starts."""
    sport, mid, pick = str(request.data.get("sport") or ""), str(request.data.get("match_id") or "")[:64], str(request.data.get("pick") or "")[:80]
    if sport not in ("cricket", "football") or not mid or not pick:
        return Response({"detail": "Pick a team."}, status=400)
    if sport == "cricket":
        allm, _ = _cricket_all()
        m = next((x for x in allm if x["id"] == mid), None)
        ok = m and not m["ended"] and pick in [t["name"] for t in m["teams"]] + ["Draw"]
    else:
        d, _ = feeds.get("football:matches")
        m = next((x for x in (d or {}).get("matches", []) if str(x["id"]) == mid), None)
        ok = m and m["status"] in ("SCHEDULED", "TIMED") and pick in (m["home"]["name"], m["away"]["name"], "Draw")
    if not ok:
        return Response({"detail": "Predictions are closed for this match."}, status=400)
    Prediction.objects.update_or_create(user=request.user, sport=sport, match_id=mid, defaults={"pick": pick})
    return Response(_votes(sport, [mid], request.user))
