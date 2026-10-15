"""/api/linkpreview/?url=... -> {title, description, image, site, url}. Used under posts that contain a link.
Our own pages are read from this server; other sites are fetched once (public addresses only, 6 s, 600 KB max)
and kept for 7 days. Nothing is fetched for private or local addresses."""
import hashlib
import html
import ipaddress
import re
import socket
from datetime import timedelta
from urllib.parse import urljoin, urlparse

from django.core.cache import cache
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import LinkPreview

OURS = {"xpertcreation.com", "www.xpertcreation.com"}
UA = "Mozilla/5.0 (compatible; XpertCreationBot/1.0; +https://xpertcreation.com)"
KEEP = timedelta(days=7)
RETRY = timedelta(hours=6)
MAXB = 600_000


def _public(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for i in infos:
        ip = ipaddress.ip_address(i[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return bool(infos)


def _get(url):
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    u = urlparse(url)
    if u.hostname in OURS:   # our own page: ask nginx on this server (same page Facebook would get)
        r = requests.get("https://127.0.0.1" + (u.path or "/") + ("?" + u.query if u.query else ""), headers={"Host": u.hostname, "User-Agent": UA},
                         timeout=6, verify=False, stream=True, allow_redirects=False)
        return url, r
    for _ in range(4):
        u = urlparse(url)
        if u.scheme not in ("http", "https") or (u.port not in (None, 80, 443)) or not u.hostname or not _public(u.hostname):
            return url, None
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html"}, timeout=6, stream=True, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            url = urljoin(url, r.headers["Location"]); r.close(); continue
        return url, r
    return url, None


def _meta(page, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*>' % re.escape(n), page, re.I)
        if m:
            c = re.search(r'content=["\']([^"\']*)["\']', m.group(0), re.I)
            if c and c.group(1).strip():
                return html.unescape(c.group(1).strip())
    return ""


def _fetch(url):
    final, r = _get(url)
    if r is None or r.status_code != 200 or "html" not in r.headers.get("Content-Type", "html"):
        return None
    data = b""
    for chunk in r.iter_content(16384):
        data += chunk
        if len(data) > MAXB or b"</head>" in data.lower():
            break
    r.close()
    page = data.decode(r.encoding or "utf-8", "ignore")
    t = _meta(page, "og:title", "twitter:title")
    if not t:
        m = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
        t = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""
    img = _meta(page, "og:image", "og:image:url", "twitter:image")
    if img:
        img = urljoin(final, img)
        if not img.startswith("https://"):
            img = ""
    return {"title": t[:300], "description": _meta(page, "og:description", "description", "twitter:description")[:500],
            "image": img[:1000], "site": (_meta(page, "og:site_name") or urlparse(final).hostname or "")[:120], "final": final[:1000]}


def _out(p):
    return {"url": p.url, "title": p.title, "description": p.description, "image": p.image, "site": p.site,
            "ours": urlparse(p.url).hostname in OURS}


@api_view(["GET"])
@permission_classes([AllowAny])
def preview(request):
    url = (request.GET.get("url") or "").strip()[:1000]
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname or len(url) < 10:
        return Response({"detail": "Bad link."}, status=400)
    key = hashlib.sha256(url.encode()).hexdigest()
    p = LinkPreview.objects.filter(key=key).first()
    now = timezone.now()
    if p and (now - p.fetched_at < (KEEP if p.ok else RETRY)):
        return Response(_out(p)) if p.ok else Response({"detail": "No preview."}, status=404)
    ip = (request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR") or "")[:64]
    n = cache.get("lp:" + ip, 0)
    if n >= 40:                       # new pages fetched per visitor per 10 minutes
        return Response({"detail": "Try again later."}, status=429)
    cache.set("lp:" + ip, n + 1, 600)
    try:
        d = _fetch(url)
    except Exception:
        d = None
    vals = dict(url=url, final_url=(d or {}).get("final", ""), site=(d or {}).get("site", ""), title=(d or {}).get("title", ""),
                description=(d or {}).get("description", ""), image=(d or {}).get("image", ""), ok=bool(d and d["title"]), fetched_at=now)
    p, _ = LinkPreview.objects.update_or_create(key=key, defaults=vals)
    return Response(_out(p)) if p.ok else Response({"detail": "No preview."}, status=404)
