"""Shows: Pakistani and Indian dramas and movies, from TMDB, plus our own reviews,
watchlists and links to official channels.

The TMDB key stays on the server: every call goes through here and is cached in Redis.
"This product uses the TMDB API but is not endorsed or certified by TMDB."
"""
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.db.models import Avg, Count
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import OfficialLink, TitleReview, WatchItem

API = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/"
LIST_TTL, TITLE_TTL, SEARCH_TTL = 6 * 3600, 24 * 3600, 3600

LISTS = {
    "pk_tv": ("/discover/tv", {"with_origin_country": "PK", "sort_by": "popularity.desc"}),
    "in_tv": ("/discover/tv", {"with_origin_country": "IN", "with_original_language": "hi", "sort_by": "popularity.desc"}),
    "pk_movie": ("/discover/movie", {"with_origin_country": "PK", "sort_by": "popularity.desc"}),
    "in_movie": ("/discover/movie", {"with_origin_country": "IN", "with_original_language": "hi",
                                     "sort_by": "popularity.desc"}),
    "trending": ("/trending/all/week", {}),
}


class _Throttle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ident = request.user.pk if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class BrowseThrottle(_Throttle):
    scope = "screen_browse"


class WriteThrottle(_Throttle):
    scope = "screen_write"


def _err(msg, code=400):
    return Response({"detail": msg}, status=code)


def _key():
    """From settings, the environment, or the .env file next to manage.py - never sent to a browser."""
    k = getattr(settings, "TMDB_API_KEY", "") or os.environ.get("TMDB_API_KEY", "")
    if k:
        return k
    for base in (getattr(settings, "BASE_DIR", ""), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        try:
            with open(os.path.join(str(base), ".env")) as f:
                for line in f:
                    if line.startswith("TMDB_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            continue
    return ""


class TMDBError(Exception):
    pass


def tmdb(path, params=None, ttl=LIST_TTL):
    params = dict(params or {})
    params.setdefault("language", "en-US")
    params.setdefault("include_adult", "false")
    ck = "tmdb:" + hashlib.sha1((path + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    hit = cache.get(ck)
    if hit is not None:
        return hit
    key = _key()
    if not key:
        raise TMDBError("no key")
    q = dict(params, api_key=key)
    url = API + path + "?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                    timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        raise TMDBError("unreachable")
    cache.set(ck, data, ttl)
    return data


def _img(path, size):
    return IMG + size + path if path else ""


def _year(d):
    return (d or "")[:4]


def _item(x, kind=None):
    kind = kind or x.get("media_type")
    if kind not in ("tv", "movie") or x.get("adult"):
        return None
    return {"kind": kind, "id": x.get("id"),
            "title": x.get("name") if kind == "tv" else x.get("title"),
            "year": _year(x.get("first_air_date") if kind == "tv" else x.get("release_date")),
            "poster": _img(x.get("poster_path"), "w342"),
            "rating": round(x.get("vote_average") or 0, 1),
            "overview": (x.get("overview") or "")[:220]}


def _list_out(data, kind=None):
    items = [i for i in (_item(x, kind) for x in data.get("results", [])) if i and i["title"]]
    return {"page": data.get("page", 1), "pages": min(data.get("total_pages", 1), 50), "results": items}


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def lists(request, name):
    if name not in LISTS:
        return _err("Unknown list.", 404)
    path, params = LISTS[name]
    try:
        page = max(1, min(50, int(request.GET.get("page") or 1)))
    except ValueError:
        page = 1
    try:
        data = tmdb(path, dict(params, page=page))
    except TMDBError:
        return _err("Could not reach the film database. Try again in a minute.", 502)
    kind = None if name == "trending" else ("tv" if name.endswith("_tv") else "movie")
    return Response(_list_out(data, kind))


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def search(request):
    q = re.sub(r"\s+", " ", str(request.GET.get("q") or "")).strip()[:80]
    if len(q) < 2:
        return Response({"page": 1, "pages": 0, "results": []})
    try:
        data = tmdb("/search/multi", {"query": q, "page": 1}, ttl=SEARCH_TTL)
    except TMDBError:
        return _err("Could not reach the film database. Try again in a minute.", 502)
    return Response(_list_out(data))


def _ours(request, kind, tid):
    agg = TitleReview.objects.filter(kind=kind, tmdb_id=tid, hidden=False).aggregate(a=Avg("stars"), n=Count("id"))
    reviews = [{"name": (r.user.full_name or "").strip() if hasattr(r.user, "full_name") else "",
                "stars": r.stars, "text": r.text, "when": r.updated_at.strftime("%d %b %Y"),
                "mine": request.user.is_authenticated and r.user_id == request.user.pk}
               for r in TitleReview.objects.filter(kind=kind, tmdb_id=tid, hidden=False).select_related("user")[:30]]
    for r in reviews:
        r["name"] = r["name"] or "A member"
    mine, listed = None, False
    if request.user.is_authenticated:
        m = TitleReview.objects.filter(user=request.user, kind=kind, tmdb_id=tid).first()
        mine = {"stars": m.stars, "text": m.text} if m else None
        listed = WatchItem.objects.filter(user=request.user, kind=kind, tmdb_id=tid).exists()
    return {"members_rating": round(agg["a"], 1) if agg["a"] else None, "members_count": agg["n"],
            "reviews": reviews, "my_review": mine, "in_list": listed,
            "official": [{"label": o.label, "url": o.url} for o in OfficialLink.objects.filter(kind=kind, tmdb_id=tid)]}


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def title(request, kind, tid):
    if kind not in ("tv", "movie"):
        return _err("Unknown kind.", 404)
    try:
        d = tmdb("/%s/%d" % (kind, tid), {"append_to_response": "credits,videos,watch/providers"}, ttl=TITLE_TTL)
    except TMDBError:
        return _err("Could not load this title. It may not exist, or the film database is busy.", 502)
    if d.get("adult") or not d.get("id"):
        return _err("Not found.", 404)
    vids = [v for v in (d.get("videos") or {}).get("results", []) if v.get("site") == "YouTube"]
    vids.sort(key=lambda v: (v.get("type") != "Trailer", v.get("type") != "Teaser", not v.get("official")))
    prov = ((d.get("watch/providers") or {}).get("results") or {})
    region = "PK" if "PK" in prov else ("IN" if "IN" in prov else None)
    where = []
    if region:
        for kind_ in ("flatrate", "free", "ads"):
            for p in prov[region].get(kind_, []) or []:
                if p.get("provider_name") not in [w["name"] for w in where]:
                    where.append({"name": p.get("provider_name"), "logo": _img(p.get("logo_path"), "w92")})
    out = {
        "kind": kind, "id": d["id"],
        "title": d.get("name") if kind == "tv" else d.get("title"),
        "original_title": d.get("original_name") if kind == "tv" else d.get("original_title"),
        "year": _year(d.get("first_air_date") if kind == "tv" else d.get("release_date")),
        "overview": d.get("overview") or "", "tagline": d.get("tagline") or "",
        "genres": [g.get("name") for g in d.get("genres", [])],
        "poster": _img(d.get("poster_path"), "w500"), "backdrop": _img(d.get("backdrop_path"), "w780"),
        "rating": round(d.get("vote_average") or 0, 1), "votes": d.get("vote_count") or 0,
        "runtime": d.get("runtime") if kind == "movie" else None,
        "seasons": d.get("number_of_seasons") if kind == "tv" else None,
        "episodes": d.get("number_of_episodes") if kind == "tv" else None,
        "networks": [n.get("name") for n in d.get("networks", [])] if kind == "tv" else [],
        "countries": d.get("origin_country") or [c.get("iso_3166_1") for c in d.get("production_countries", [])],
        "cast": [{"name": c.get("name"), "character": c.get("character") or "", "photo": _img(c.get("profile_path"), "w185")}
                 for c in ((d.get("credits") or {}).get("cast") or [])[:12]],
        "trailer": vids[0]["key"] if vids else "",
        "where": where, "where_region": region,
    }
    out.update(_ours(request, kind, tid))
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([WriteThrottle])
def review(request, kind, tid):
    if kind not in ("tv", "movie"):
        return _err("Unknown kind.", 404)
    try:
        stars = int(request.data.get("stars"))
    except (TypeError, ValueError):
        stars = -1
    if stars == 0:
        TitleReview.objects.filter(user=request.user, kind=kind, tmdb_id=tid).delete()
        return Response(_ours(request, kind, tid))
    if not 1 <= stars <= 5:
        return _err("Pick from one to five stars.")
    if not getattr(request.user, "is_email_verified", True):
        return _err("Verify your email before reviewing.", 403)
    text = str(request.data.get("text") or "").replace("\r\n", "\n").strip()[:1000]
    TitleReview.objects.update_or_create(user=request.user, kind=kind, tmdb_id=tid,
                                         defaults={"stars": stars, "text": text})
    return Response(_ours(request, kind, tid))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([WriteThrottle])
def toggle_list(request, kind, tid):
    if kind not in ("tv", "movie"):
        return _err("Unknown kind.", 404)
    old = WatchItem.objects.filter(user=request.user, kind=kind, tmdb_id=tid).first()
    if old:
        old.delete()
        return Response({"in_list": False})
    if WatchItem.objects.filter(user=request.user).count() >= 500:
        return _err("Your list is full. Remove something first.")
    poster = str(request.data.get("poster") or "")
    if not poster.startswith(IMG):
        poster = ""
    WatchItem.objects.create(user=request.user, kind=kind, tmdb_id=tid,
                             title=str(request.data.get("title") or "Untitled")[:200],
                             poster=poster[:200], year=str(request.data.get("year") or "")[:4])
    return Response({"in_list": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([BrowseThrottle])
def my_list(request):
    return Response({"results": [{"kind": w.kind, "id": w.tmdb_id, "title": w.title, "poster": w.poster,
                                  "year": w.year, "rating": None, "overview": ""}
                                 for w in WatchItem.objects.filter(user=request.user)[:500]]})
