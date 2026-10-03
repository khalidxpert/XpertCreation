"""Read a YouTube channel's public feed (no API key) and resolve a channel link to its id."""
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone as tz

UA = {"User-Agent": "Mozilla/5.0 (compatible; XpertCreation/1.0; +https://xpertcreation.com)", "Accept-Language": "en"}
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode("utf-8", "ignore")


def resolve(link):
    """'youtube.com/@Name', '/channel/UC...', or a bare UC id -> (channel_id, name)."""
    link = (link or "").strip()
    m = re.search(r"(UC[\w-]{22})", link)
    if m and "/channel/" in link or re.fullmatch(r"UC[\w-]{22}", link):
        cid = m.group(1)
    else:
        if not link.startswith("http"):
            link = "https://www.youtube.com/" + link.lstrip("/")
        page = _get(link)
        m = re.search(r'<meta itemprop="identifier" content="(UC[\w-]{22})"', page) or re.search(r'"channelId":"(UC[\w-]{22})"', page) \
            or re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', page)
        if not m:
            return None, ""
        cid = m.group(1)
    name = ""
    try:
        feed = ET.fromstring(_get("https://www.youtube.com/feeds/videos.xml?channel_id=" + cid))
        name = (feed.findtext("a:title", default="", namespaces=NS) or "").strip()
    except Exception:
        pass
    return cid, name


def latest(cid):
    """[(video_id, title, published datetime)] newest first, from the channel's public feed."""
    feed = ET.fromstring(_get("https://www.youtube.com/feeds/videos.xml?channel_id=" + cid))
    out = []
    for e in feed.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", default="", namespaces=NS); title = e.findtext("a:title", default="", namespaces=NS)
        pub = e.findtext("a:published", default="", namespaces=NS)
        try:
            when = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except ValueError:
            when = datetime.now(tz.utc)
        if vid and "/shorts/" not in (e.find("a:link", NS).get("href", "") if e.find("a:link", NS) is not None else ""):
            out.append((vid, title[:200], when))
    return out
