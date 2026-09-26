"""Real titles, descriptions, preview pictures and structured data for pages that the browser fills in:
jobs, posts, profiles, adoption listings, dramas and films. Google and WhatsApp read the page before any
script runs, so the server puts the right tags in the page itself. The page and its script stay the same.
Data comes from the site's own API views, called as a signed-out visitor, so private things stay private.
Also /sitemap-dynamic.xml: live list of public jobs, profiles, adoption listings, public posts and shows."""
import html
import json
import re

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import resolve
from django.utils import timezone

LAND = "/var/www/xpertcreation-landing/"
SITE = "https://xpertcreation.com"
COVER = SITE + "/brand/og-cover.jpg"
_rf = RequestFactory()


def _api(path):
    """Ask one of the site's own API views, as a signed-out visitor. Returns the data or None."""
    try:
        m = resolve(path)
        req = _rf.get(path, HTTP_HOST="xpertcreation.com", secure=True)
        req.user = AnonymousUser()
        r = m.func(req, *m.args, **m.kwargs)
        return r.data if getattr(r, "status_code", 500) == 200 else None
    except Exception:
        return None


def _clip(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "\u2026"


def _abs(u):
    u = str(u or "")
    return u if u.startswith("http") else (SITE + u if u.startswith("/") else "")


def _page(template, title, desc, url, image="", ld=None, noindex=False, status=200):
    key = "seo:%s:%s" % (template, url)
    try:
        src = open(LAND + template, encoding="utf-8").read()
    except OSError:
        return HttpResponse("Not found", status=404)
    t, d, img = html.escape(title, quote=True), html.escape(desc, quote=True), html.escape(image or COVER, quote=True)
    s = re.sub(r"<title>.*?</title>", "<title>%s</title>" % t, src, 1, re.S)
    s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % d, s, 1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">\s*', "", s)
    s = re.sub(r'<meta (?:property|name)="(?:og|twitter):[^"]*" content="[^"]*">\s*', "", s)
    s = re.sub(r'<meta name="robots" content="[^"]*">\s*', "", s)
    s = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', "", s, flags=re.S)   # the template's own, generic one
    head = ['<link rel="canonical" href="%s">' % html.escape(url, quote=True),
            '<meta property="og:type" content="website">', '<meta property="og:site_name" content="XpertCreation">',
            '<meta property="og:title" content="%s">' % t, '<meta property="og:description" content="%s">' % d,
            '<meta property="og:url" content="%s">' % html.escape(url, quote=True), '<meta property="og:image" content="%s">' % img,
            '<meta name="twitter:card" content="summary_large_image">', '<meta name="twitter:title" content="%s">' % t,
            '<meta name="twitter:description" content="%s">' % d, '<meta name="twitter:image" content="%s">' % img]
    if noindex:
        head.append('<meta name="robots" content="noindex,follow">')
    if ld:
        head.append('<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"))
    s = s.replace("</head>", "\n".join(head) + "\n</head>", 1)
    resp = HttpResponse(s, status=status, content_type="text/html; charset=utf-8")
    resp["Cache-Control"] = "public, max-age=300"
    return resp


def job(request, pk):
    d = _api("/api/jobs/%s/" % pk)
    url = "%s/job/%s" % (SITE, pk)
    if not d or "job" not in d:
        return _page("jobs.html", "Job not found \u2014 XpertCreation Jobs", "This job is no longer available. See other free jobs on XpertCreation.", url, noindex=True, status=404)
    j = d["job"]
    where = "Remote" if j.get("workplace") == "remote" and not j.get("city") else ", ".join(x for x in (j.get("city"), j.get("country")) if x)
    title = _clip("%s at %s%s" % (j["title"], j["company"], (" \u2014 " + where) if where else ""), 70)
    desc = _clip("%s job%s. %s" % (j.get("kind_label", ""), (" in " + where) if where else "", j.get("description", "")), 158)
    ld = {"@context": "https://schema.org", "@type": "JobPosting", "title": j["title"],
          "description": html.escape(j.get("description", "")).replace("\n", "<br>"),
          "datePosted": (j.get("posted_iso") or "")[:10], "validThrough": j.get("deadline", "") + "T23:59",
          "employmentType": (j.get("kind") or "").upper(), "directApply": True,
          "hiringOrganization": {"@type": "Organization", "name": j["company"]}}
    if j.get("workplace") == "remote":
        ld["jobLocationType"] = "TELECOMMUTE"
        if j.get("country"):
            ld["applicantLocationRequirements"] = {"@type": "Country", "name": j["country"]}
    if j.get("city"):
        ld["jobLocation"] = {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": j["city"],
                                                          "addressRegion": j.get("state", ""), "addressCountry": j.get("country", "")}}
    s = j.get("salary")
    if s:
        ld["baseSalary"] = {"@type": "MonetaryAmount", "currency": s.get("currency", "PKR"), "value": {
            "@type": "QuantitativeValue", "minValue": s.get("min") or s.get("max"), "maxValue": s.get("max") or s.get("min"),
            "unitText": {"month": "MONTH", "year": "YEAR", "hour": "HOUR"}.get(s.get("period"), "MONTH")}}
    return _page("jobs.html", title + " \u2014 XpertCreation Jobs" if len(title) < 45 else title, desc, url,
                 ld=ld if j.get("open") else None, noindex=not j.get("open"))


def post(request, pk):
    d = _api("/api/feed/posts/%s/" % pk)
    url = "%s/post/%s" % (SITE, pk)
    if not d or "post" not in d:
        return _page("feed.html", "Post \u2014 XpertCreation Connect", "A post on XpertCreation Connect. Sign in to see posts shared with members.", url, noindex=True)
    p = d["post"]
    name = p.get("author", {}).get("name", "A member")
    body = _clip(p.get("body", ""), 150) or "A photo"
    ld = {"@context": "https://schema.org", "@type": "SocialMediaPosting", "headline": _clip(p.get("body", "") or "Post", 100),
          "author": {"@type": "Person", "name": name}, "url": url}
    return _page("feed.html", _clip("%s: \u201c%s\u201d" % (name, _clip(p.get("body", ""), 50) or "Photo"), 68) + " \u2014 XpertCreation",
                 body, url, image=_abs((p.get("images") or [""])[0]), ld=ld)


def adopt(request, pk):
    d = _api("/api/pets/adopt/%s/" % pk)
    url = "%s/adopt/%s" % (SITE, pk)
    if not d or "name" not in d:
        return _page("adopt.html", "Pet not available \u2014 XpertCreation Adopt", "This pet is no longer listed. See other pets looking for a home.", url, noindex=True, status=404)
    kind = {"dog": "Dog", "cat": "Cat", "bird": "Bird", "rabbit": "Rabbit"}.get(d.get("species"), "Pet")
    title = _clip("Adopt %s \u2014 %s%s in %s" % (d["name"], kind, (", " + d["breed"]) if d.get("breed") else "", d.get("city", "")), 68)
    desc = _clip("Free adoption: %s, %s. %s" % (d["name"], ", ".join(x for x in (d.get("age"), "vaccinated" if d.get("vaccinated") else "") if x), d.get("description", "")), 158)
    return _page("adopt.html", title, desc, url, image=_abs((d.get("photos") or [""])[0]), noindex=d.get("status") not in ("available", "reserved"))


def _pick(d, *keys):
    """First non-empty value among these keys, looking one level into nested dicts too."""
    if not isinstance(d, dict):
        return ""
    for k in keys:
        if d.get(k):
            return d[k]
    for v in d.values():
        if isinstance(v, dict):
            r = _pick(v, *keys)
            if r:
                return r
    return ""


def profile(request, slug):
    d = _api("/api/network/in/%s/" % slug)
    url = "%s/in/%s" % (SITE, slug)
    if not d:
        return _page("in.html", "Member profile \u2014 XpertCreation Connect", "A member profile on XpertCreation Connect.", url, noindex=True)
    name, head = str(_pick(d, "name", "full_name")), str(_pick(d, "headline"))
    city = str(_pick(d, "city"))
    title = _clip(name + (" \u2014 " + head if head else ""), 68)
    desc = _clip("%s%s%s on XpertCreation Connect. %s" % (name, (", " + head) if head else "", (" in " + city) if city else "", _pick(d, "about")), 158)
    ld = {"@context": "https://schema.org", "@type": "ProfilePage", "mainEntity": {"@type": "Person", "name": name, "jobTitle": head, "url": url}}
    return _page("in.html", title, desc, url, image=_abs(_pick(d, "avatar_url", "avatar")), ld=ld)


def show(request, kind, pk):
    d = _api("/api/screen/title/%s/%s/" % (kind, pk))
    url = "%s/show/%s-%s" % (SITE, kind, pk)
    if not d:
        return _page("show.html", "Drama or film \u2014 XpertCreation Shows", "Pakistani and Indian dramas and films: story, cast, trailer and where to watch.", url)
    name = str(_pick(d, "title", "name"))
    year = str(_pick(d, "year", "first_air_date", "release_date"))[:4]
    what = "drama" if kind == "tv" else "film"
    title = _clip("%s%s \u2014 story, cast, trailer" % (name, (" (%s)" % year) if year else ""), 68)
    desc = _clip("%s %s: story, cast, trailer, reviews and where to watch. %s" % (name, what, _pick(d, "overview", "description", "story")), 158)
    poster = _pick(d, "poster_url", "poster", "image", "backdrop_url")
    if poster and str(poster).startswith("/") and not str(poster).startswith("/media"):
        poster = "https://image.tmdb.org/t/p/w500" + poster
    ld = {"@context": "https://schema.org", "@type": "TVSeries" if kind == "tv" else "Movie", "name": name, "url": url}
    if poster:
        ld["image"] = _abs(poster) if str(poster).startswith("/") else poster
    return _page("show.html", title, desc, url, image=_abs(poster) if str(poster).startswith("/") else str(poster), ld=ld)


def sitemap(request):
    xml = cache.get("seo:sitemap")
    if not xml:
        urls = []
        try:
            from jobs.models import Job
            for j in Job.objects.filter(closed=False, hidden=False, deadline__gte=timezone.localdate()).values("id", "updated_at")[:5000]:
                urls.append(("/job/%d" % j["id"], j["updated_at"]))
        except Exception:
            pass
        try:
            from network.models import ProProfile
            for p in ProProfile.objects.filter(visibility="public").exclude(headline="").values("slug")[:5000]:
                urls.append(("/in/%s" % p["slug"], None))
        except Exception:
            pass
        try:
            from pets.models import AdoptionPost
            for a in AdoptionPost.objects.filter(hidden=False, status="available").values("id", "created_at")[:5000]:
                urls.append(("/adopt/%d" % a["id"], a["created_at"]))
        except Exception:
            pass
        try:
            from feed.models import Post
            for p in Post.objects.filter(hidden=False, visibility="public").values("id", "created_at")[:2000]:
                urls.append(("/post/%d" % p["id"], p["created_at"]))
        except Exception:
            pass
        try:
            from screen.models import TitleReview, WatchItem
            seen = set()
            for m in (TitleReview, WatchItem):
                for r in m.objects.values("kind", "tmdb_id").distinct()[:3000]:
                    seen.add((r["kind"], r["tmdb_id"]))
            urls += [("/show/%s-%s" % (k, i), None) for k, i in sorted(seen)]
        except Exception:
            pass
        rows = ["<url><loc>%s%s</loc>%s</url>" % (SITE, u, ("<lastmod>%s</lastmod>" % t.date().isoformat()) if t else "") for u, t in urls]
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
        cache.set("seo:sitemap", xml, 3600)
    return HttpResponse(xml, content_type="application/xml")
