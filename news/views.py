import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape

from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

log = logging.getLogger(__name__)

# Headline and link only, straight from each publisher's own feed. Reproducing
# whole articles would be someone else's work on our page; a headline that
# links back is what RSS is for.
FEEDS = {
    "pk": [
        ("Dawn",     "https://www.dawn.com/feeds/home"),
        ("Geo News", "https://www.geo.tv/rss/1/1"),
        ("BBC Urdu", "https://feeds.bbci.co.uk/urdu/rss.xml"),
    ],
    "world": [
        ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
}

TTL = 900   # 15 minutes: news moves, but not every thirty seconds


class NewsThrottle(SimpleRateThrottle):
    scope = "news"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def clean(text, limit=200):
    """Strip tags and entities out of a description, then trim it."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit] + ("\u2026" if len(text) > limit else "")


def fetch_feed(name, url, limit=6):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "XpertCreation/1.0"})
        with urllib.request.urlopen(req, timeout=7) as r:
            raw = r.read()
    except Exception:
        log.warning("Feed unreachable: %s", name)
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        log.warning("Feed did not parse: %s", name)
        return []

    out = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        if not title or not link:
            continue
        out.append({
            "title": clean(title, 160),
            "link": link.strip(),
            "source": name,
            "summary": clean(item.findtext("description"), 180),
            "when": (item.findtext("pubDate") or "")[:16],
        })
        if len(out) >= limit:
            break
    return out


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([NewsThrottle])
def headlines(request):
    """?region=pk|world"""
    region = request.GET.get("region", "pk")
    if region not in FEEDS:
        region = "pk"

    ck = "news:" + region
    hit = cache.get(ck)
    if hit is not None:
        return Response({"region": region, "items": hit, "cached": True})

    items = []
    for name, url in FEEDS[region]:
        items.extend(fetch_feed(name, url))

    # Interleave the sources so one publisher does not take the whole strip.
    by_source = {}
    for it in items:
        by_source.setdefault(it["source"], []).append(it)
    mixed, i = [], 0
    while any(by_source.values()):
        for src in list(by_source):
            if by_source[src]:
                mixed.append(by_source[src].pop(0))
        i += 1
        if i > 12:
            break

    mixed = mixed[:15]
    if mixed:
        cache.set(ck, mixed, TTL)
    return Response({"region": region, "items": mixed, "cached": False})
