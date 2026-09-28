"""Hashtag pages: /tag/<name> lists every public Connect post with #name. Own title and description for Google,
and /sitemap-tags.xml lists the tags. Reads feed posts only - never changes them."""
import html
import re
from collections import Counter

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

SITE = "https://xpertcreation.com"
LAND = "/var/www/xpertcreation-landing/"
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,49}$")
TAG_IN_TEXT = re.compile(r"(?:^|[\s(])#([A-Za-z][A-Za-z0-9_]{1,49})")
PER_PAGE = 20


def _posts(name):
    from feed.models import Post
    return (Post.objects.filter(visibility="public", hidden=False, body__iregex=r"(^|[\s(])#%s([^A-Za-z0-9_]|$)" % re.escape(name))
            .select_related("author").order_by("-created_at"))


def _media(p):
    return (settings.MEDIA_URL.rstrip("/") + "/" + p) if p and not str(p).startswith(("http", "/")) else (p or "")


def _avatar(u):
    a = getattr(u, "avatar", None)
    try:
        return a.url if a and hasattr(a, "url") else _media(str(a or ""))
    except Exception:
        return ""


@api_view(["GET"])
@permission_classes([AllowAny])
def tag_posts(request, name):
    if not NAME.match(name):
        return Response({"detail": "Not a hashtag."}, status=404)
    try:
        page = max(1, int(request.GET.get("page") or 1))
    except ValueError:
        page = 1
    qs = _posts(name)
    total = qs.count()
    rows = qs[(page - 1) * PER_PAGE: page * PER_PAGE]
    return Response({"tag": name.lower(), "total": total, "page": page, "more": page * PER_PAGE < total,
                     "posts": [{"id": p.id, "body": p.body, "image": _media((p.images or [None])[0]) if p.images else "",
                                "author": getattr(p.author, "full_name", "") or "Member", "avatar": _avatar(p.author),
                                "when": timezone.localtime(p.created_at).strftime("%d %b %Y"),
                                "reactions": p.reactions_count, "comments": p.comments_count} for p in rows]})


def popular_tags(limit=60):
    key = "tags:popular"
    hit = cache.get(key)
    if hit is not None:
        return hit
    from feed.models import Post
    c = Counter()
    for body in Post.objects.filter(visibility="public", hidden=False).order_by("-created_at").values_list("body", flat=True)[:3000]:
        c.update({t.lower() for t in TAG_IN_TEXT.findall(body or "")})
    out = [{"tag": t, "count": n} for t, n in c.most_common(limit)]
    cache.set(key, out, 1800)
    return out


@api_view(["GET"])
@permission_classes([AllowAny])
def popular(request):
    return Response({"tags": popular_tags(40)})


def page(request, name):
    """/tag/<name>: the page with its own title and description; capitals go to the lowercase address."""
    if not NAME.match(name):
        return HttpResponse("Not found", status=404)
    if name != name.lower():
        return HttpResponsePermanentRedirect("/tag/" + name.lower())
    try:
        src = open(LAND + "tag.html", encoding="utf-8").read()
    except OSError:
        return HttpResponse("Not found", status=404)
    n = _posts(name).count()
    e = lambda v: html.escape(v, quote=True)
    title = "#%s \u2014 posts on XpertCreation Connect" % name
    desc = ("%d post%s tagged #%s on XpertCreation Connect. Free tools, courses, jobs, sports and more." % (n, "" if n == 1 else "s", name)) if n else \
           "Posts tagged #%s on XpertCreation Connect." % name
    s = re.sub(r"<title>.*?</title>", "<title>%s</title>" % e(title), src, 1, re.S)
    s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % e(desc), s, 1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s/tag/%s">' % (SITE, name), s, 1)
    s = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="%s">' % e(title), s, 1)
    s = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="%s">' % e(desc), s, 1)
    s = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s/tag/%s">' % (SITE, name), s, 1)
    if n == 0:
        s = s.replace("</head>", '<meta name="robots" content="noindex">\n</head>', 1)
    r = HttpResponse(s, content_type="text/html; charset=utf-8", status=200 if n else 404)
    r["Cache-Control"] = "public, max-age=300"
    return r


def sitemap(request):
    urls = ["  <url><loc>%s/tag/%s</loc><changefreq>daily</changefreq></url>" % (SITE, t["tag"]) for t in popular_tags(500)]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    r = HttpResponse(xml, content_type="application/xml")
    r["Cache-Control"] = "public, max-age=1800"
    return r
