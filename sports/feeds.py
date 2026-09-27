"""Fetching from the three providers. Only the refresh command and the scorecard view call these;
pages read the saved copies. Keys live in .env: CRICAPI_KEY, FOOTBALL_DATA_KEY, SPORTSDB_KEY."""
import os
from datetime import timedelta

import requests
from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .models import ApiUse, SportsData

LIMITS = {"cricapi": 90, "football": 4000, "sportsdb": 3000}      # per day; CricAPI's free plan is 100
FOOTBALL_CODES = ["PL", "CL", "PD", "SA", "BL1", "FL1", "ELC", "PPL", "DED", "BSA", "EC", "WC", "CLI"]


def env(name, default=""):
    v = os.environ.get(name, "")
    if v:
        return v
    try:
        with open(os.path.join(str(settings.BASE_DIR), ".env")) as f:
            for line in f:
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return default


def used(provider):
    row = ApiUse.objects.filter(provider=provider, day=timezone.localdate()).first()
    return row.count if row else 0


def spend(provider):
    row, _ = ApiUse.objects.get_or_create(provider=provider, day=timezone.localdate())
    ApiUse.objects.filter(pk=row.pk).update(count=F("count") + 1)


def can(provider, reserve=0):
    return used(provider) < LIMITS[provider] - reserve


def get(key):
    row = SportsData.objects.filter(key=key).first()
    return (row.data, row.fetched_at) if row else (None, None)


def put(key, data):
    SportsData.objects.update_or_create(key=key, defaults={"data": data, "fetched_at": timezone.now()})


def age(key):
    _, at = get(key)
    return (timezone.now() - at).total_seconds() if at else 1e9


def _json(provider, url, params=None, headers=None):
    if not can(provider):
        return None
    spend(provider)
    try:
        r = requests.get(url, params=params, headers=headers or {}, timeout=15)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


# ---------------------------------------------------------------- cricket (CricketData.org)

def cricapi(path, **params):
    params["apikey"] = env("CRICAPI_KEY")
    d = _json("cricapi", "https://api.cricapi.com/v1/" + path, params)
    if d and d.get("info", {}).get("hitsToday") is not None:
        row, _ = ApiUse.objects.get_or_create(provider="cricapi", day=timezone.localdate())
        ApiUse.objects.filter(pk=row.pk).update(count=max(row.count, int(d["info"]["hitsToday"])))
    return d if d and d.get("status") == "success" else None


def cricket_match(m):
    teams = m.get("teams") or []
    info = {t.get("name"): t for t in (m.get("teamInfo") or [])}
    return {"id": m.get("id"), "name": m.get("name", ""), "type": (m.get("matchType") or "").upper(), "status": m.get("status", ""),
            "venue": m.get("venue", ""), "date": m.get("dateTimeGMT") or m.get("date", ""), "series_id": m.get("series_id", ""),
            "started": bool(m.get("matchStarted")), "ended": bool(m.get("matchEnded")),
            "teams": [{"name": t, "short": (info.get(t) or {}).get("shortname", ""), "img": (info.get(t) or {}).get("img", "")} for t in teams],
            "score": [{"inning": s.get("inning", ""), "r": s.get("r"), "w": s.get("w"), "o": s.get("o")} for s in (m.get("score") or [])]}


def refresh_cricket(force=False):
    """Current matches (live and just finished) every 20 min while something is live, hourly otherwise;
    the full list with upcoming games every 6 hours. About 40-70 of the 100 free requests a day."""
    cur, _ = get("cricket:current")
    live = any(m["started"] and not m["ended"] for m in (cur or {}).get("matches", []))
    n = 0
    if force or age("cricket:current") > (1800 if live else 3600):
        d = cricapi("currentMatches", offset=0)
        if d:
            put("cricket:current", {"matches": [cricket_match(m) for m in d.get("data") or []]}); n += 1
    if force or age("cricket:list") > 6 * 3600:
        allm = []
        for off in (0, 25, 50):                      # the list comes 25 at a time; upcoming games are on later pages
            d = cricapi("matches", offset=off)
            if not d:
                break
            allm += [cricket_match(m) for m in d.get("data") or []]; n += 1
            if len(d.get("data") or []) < 25:
                break
        if allm:
            put("cricket:list", {"matches": allm})
    return n


def cricket_scorecard(mid):
    """Fetched when someone opens a match: saved for 10 minutes while it's live, for good once it ends.
    Keeps 25 requests a day spare for the scheduled refresh."""
    key = "cricket:card:" + mid
    data, at = get(key)
    if data and (data.get("ended") or (timezone.now() - at).total_seconds() < 600):
        return data
    if not can("cricapi", reserve=25):
        return data
    d = cricapi("match_scorecard", id=mid)
    if not d:
        return data
    m = d.get("data") or {}
    card = cricket_match(m)
    card["toss"] = " ".join(x for x in [m.get("tossWinner", ""), ("chose to " + m["tossChoice"]) if m.get("tossChoice") else ""] if x)
    card["innings"] = []
    for inn in m.get("scorecard") or []:
        card["innings"].append({
            "inning": inn.get("inning", ""),
            "batting": [{"name": (b.get("batsman") or {}).get("name", ""), "out": b.get("dismissal-text", ""), "r": b.get("r"), "b": b.get("b"),
                         "4s": b.get("4s"), "6s": b.get("6s"), "sr": b.get("sr")} for b in inn.get("batting") or []],
            "bowling": [{"name": (b.get("bowler") or {}).get("name", ""), "o": b.get("o"), "m": b.get("m"), "r": b.get("r"), "w": b.get("w"),
                         "eco": b.get("eco")} for b in inn.get("bowling") or []],
            "extras": inn.get("extras") or {}, "totals": inn.get("totals") or {}})
    put(key, card)
    return card


# ---------------------------------------------------------------- football (football-data.org)

def fdata(path, **params):
    return _json("football", "https://api.football-data.org/v4/" + path, params, {"X-Auth-Token": env("FOOTBALL_DATA_KEY")})


def football_match(m):
    s = m.get("score") or {}
    ft = s.get("fullTime") or {}
    c = m.get("competition") or {}
    def team(t):
        return {"id": t.get("id"), "name": t.get("shortName") or t.get("name") or "TBC", "crest": t.get("crest", "")}
    return {"id": m.get("id"), "date": m.get("utcDate", ""), "status": m.get("status", ""), "minute": m.get("minute"),
            "matchday": m.get("matchday"), "stage": m.get("stage", ""),
            "comp": {"code": c.get("code", ""), "name": c.get("name", ""), "emblem": c.get("emblem", "")},
            "home": team(m.get("homeTeam") or {}), "away": team(m.get("awayTeam") or {}),
            "score": {"home": ft.get("home"), "away": ft.get("away"), "winner": s.get("winner")}}


def refresh_football(force=False):
    """Matches from 3 days back to 7 days ahead: every 2 minutes while a game is on, every 30 otherwise.
    League tables every 3 hours (one competition per run, so we stay under 10 requests a minute)."""
    n = 0
    today = timezone.localdate()
    codes = [c["code"] for c in (get("football:comps")[0] or {}).get("comps", [])] or FOOTBALL_CODES
    def live_in(code):
        d, _ = get("football:m:" + code)
        return any(m["status"] in ("IN_PLAY", "PAUSED") for m in (d or {}).get("matches", []))
    due = [c for c in codes if force or age("football:m:" + c) > (120 if live_in(c) else 1800)]
    due.sort(key=lambda c: (not live_in(c), -age("football:m:" + c)))
    for code in due[:3 if not force else 6]:          # at most 3 a run: well under the free 10-a-minute limit
        d = fdata("competitions/%s/matches" % code)          # the whole season: works through international breaks
        if d is not None and "matches" in d:
            ms = [football_match(m) for m in d.get("matches") or []]
            now = timezone.now().strftime("%Y-%m-%dT%H:%M")
            live = [m for m in ms if m["status"] in ("IN_PLAY", "PAUSED")]
            done = sorted([m for m in ms if m["status"] == "FINISHED"], key=lambda m: m["date"], reverse=True)[:20]
            soon = sorted([m for m in ms if m["status"] in ("SCHEDULED", "TIMED") and m["date"][:16] >= now], key=lambda m: m["date"])
            if soon:
                horizon = max(soon[0]["date"][:10], str(today + timedelta(days=21)))
                soon = [m for m in soon if m["date"][:10] <= horizon][:30]
            put("football:m:" + code, {"matches": live + soon + done}); n += 1
    if force or age("football:comps") > 24 * 3600:
        d = fdata("competitions")
        if d and d.get("competitions"):
            put("football:comps", {"comps": [{"code": c.get("code"), "name": c.get("name"), "emblem": c.get("emblem", ""),
                                              "area": (c.get("area") or {}).get("name", "")} for c in d["competitions"]]}); n += 1
    comps = [c["code"] for c in (get("football:comps")[0] or {}).get("comps", [])] or FOOTBALL_CODES
    stale = sorted(comps, key=lambda c: -age("football:table:" + c))
    for code in stale[:2 if force else 1]:
        if age("football:table:" + code) < 3 * 3600 and not force:
            break
        d = fdata("competitions/%s/standings" % code)
        if d and d.get("standings") is not None:
            tot = next((s for s in d["standings"] if s.get("type") == "TOTAL"), (d["standings"] or [{}])[0] if d["standings"] else {})
            put("football:table:" + code, {"comp": (d.get("competition") or {}).get("name", code), "season": (d.get("season") or {}).get("startDate", "")[:4],
                                          "table": [{"pos": r.get("position"), "team": (r.get("team") or {}).get("shortName") or (r.get("team") or {}).get("name"),
                                                     "crest": (r.get("team") or {}).get("crest", ""), "p": r.get("playedGames"), "w": r.get("won"),
                                                     "d": r.get("draw"), "l": r.get("lost"), "gd": r.get("goalDifference"), "pts": r.get("points"),
                                                     "form": r.get("form") or ""} for r in (tot.get("table") or [])]}); n += 1
    return n


# ---------------------------------------------------------------- other sports (TheSportsDB, free key)

# The free TheSportsDB key only returns a few events per request, but "events on a day" works per sport,
# so we ask day by day: 3 days back and 6 ahead. One sport per run keeps us under its rate limit.
OTHER = [("hockey", "Hockey", ["Field_Hockey", "Ice_Hockey"]),
         ("f1", "Motorsport", ["Motorsport"]),
         ("tennis", "Tennis", ["Tennis"]),
         ("kabaddi", "Kabaddi", ["Kabaddi"]),
         ("basketball", "Basketball", ["Basketball"]),
         ("mma", "Fighting", ["Fighting"])]


def sdb(path, **params):
    return _json("sportsdb", "https://www.thesportsdb.com/api/v1/json/%s/%s" % (env("SPORTSDB_KEY", "123"), path), params)


def sdb_event(e):
    return {"id": e.get("idEvent"), "name": e.get("strEvent", ""), "date": e.get("dateEvent", ""), "time": e.get("strTime", ""),
            "home": e.get("strHomeTeam", ""), "away": e.get("strAwayTeam", ""), "hs": e.get("intHomeScore"), "as": e.get("intAwayScore"),
            "league": e.get("strLeague", ""), "venue": e.get("strVenue", ""), "status": e.get("strStatus", ""), "thumb": e.get("strThumb") or ""}


def refresh_other(force=False):
    n = 0
    today = timezone.localdate()
    due = sorted([k for k, _, _ in OTHER if force or age("other:" + k) > 6 * 3600], key=lambda k: -age("other:" + k))
    for k in due[:len(OTHER) if force else 1]:
        label, sports = next((l, sp) for kk, l, sp in OTHER if kk == k)
        evs = []
        for sp in sports:
            for off in range(-3, 7):
                d = sdb("eventsday.php", d=str(today + timedelta(days=off)), s=sp); n += 1
                evs += [sdb_event(e) for e in ((d or {}).get("events") or [])]
        seen, uniq = set(), []
        for e in evs:
            if e["id"] not in seen:
                seen.add(e["id"]); uniq.append(e)
        t = str(today)
        put("other:" + k, {"label": label,
                           "next": sorted([e for e in uniq if e["date"] >= t and e["hs"] in (None, "")], key=lambda e: (e["date"], e["time"]))[:40],
                           "past": sorted([e for e in uniq if e["date"] < t or e["hs"] not in (None, "")], key=lambda e: (e["date"], e["time"]), reverse=True)[:40]})
    return n
