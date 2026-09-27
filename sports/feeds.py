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
    if force or age("cricket:current") > (1200 if live else 3600):
        d = cricapi("currentMatches", offset=0)
        if d:
            put("cricket:current", {"matches": [cricket_match(m) for m in d.get("data") or []]}); n += 1
    if force or age("cricket:list") > 6 * 3600:
        d = cricapi("matches", offset=0)
        if d:
            put("cricket:list", {"matches": [cricket_match(m) for m in d.get("data") or []]}); n += 1
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
    cur, _ = get("football:matches")
    live = any(m["status"] in ("IN_PLAY", "PAUSED") for m in (cur or {}).get("matches", []))
    if force or age("football:matches") > (120 if live else 1800):
        today = timezone.localdate()
        d = fdata("matches", dateFrom=str(today - timedelta(days=3)), dateTo=str(today + timedelta(days=7)))
        if d is not None and "matches" in d:
            put("football:matches", {"matches": [football_match(m) for m in d.get("matches") or []]}); n += 1
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

OTHER = [("hockey", "Hockey", ["FIH Pro League", "Hockey India League", "NHL", "FIH Hockey World Cup", "Men's FIH Hockey World Cup"]),
         ("f1", "Formula 1", ["Formula 1"]),
         ("tennis", "Tennis", ["ATP World Tour", "WTA Tour", "ATP Tour"]),
         ("kabaddi", "Kabaddi", ["Pro Kabaddi League", "Kabaddi World Cup"]),
         ("basketball", "Basketball", ["NBA"]),
         ("mma", "UFC", ["UFC"])]


def sdb(path, **params):
    return _json("sportsdb", "https://www.thesportsdb.com/api/v1/json/%s/%s" % (env("SPORTSDB_KEY", "123"), path), params)


def sdb_event(e):
    return {"id": e.get("idEvent"), "name": e.get("strEvent", ""), "date": e.get("dateEvent", ""), "time": e.get("strTime", ""),
            "home": e.get("strHomeTeam", ""), "away": e.get("strAwayTeam", ""), "hs": e.get("intHomeScore"), "as": e.get("intAwayScore"),
            "league": e.get("strLeague", ""), "venue": e.get("strVenue", ""), "status": e.get("strStatus", ""), "thumb": e.get("strThumb") or ""}


def refresh_other(force=False):
    """Leagues are looked up by name once a week; their next and last events every 6 hours."""
    n = 0
    if force or age("other:leagues") > 7 * 24 * 3600:
        d = sdb("all_leagues.php")
        if d and d.get("leagues"):
            names = {l.get("strLeague"): l.get("idLeague") for l in d["leagues"]}
            put("other:leagues", {k: [[nm, names[nm]] for nm in wanted if nm in names] for k, _, wanted in OTHER}); n += 1
    leagues, _ = get("other:leagues")
    for k, label, _ in OTHER:
        if not force and age("other:" + k) < 6 * 3600:
            continue
        out = {"label": label, "next": [], "past": []}
        for nm, lid in (leagues or {}).get(k, [])[:3]:
            nx = sdb("eventsnextleague.php", id=lid); ps = sdb("eventspastleague.php", id=lid); n += 2
            out["next"] += [sdb_event(e) for e in ((nx or {}).get("events") or [])[:10]]
            out["past"] += [sdb_event(e) for e in ((ps or {}).get("events") or [])[:10]]
        put("other:" + k, out)
    return n
