"""Read a book link from Internet Archive, Project Gutenberg or Wikisource and fetch its details."""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; XpertCreation/1.0; +https://xpertcreation.com)", "Accept": "application/json"}


def _json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read().decode("utf-8", "ignore"))


def _first(v):
    return (v[0] if isinstance(v, list) and v else v) or ""


def parse(link):
    """-> dict(source, source_id, source_url, title, author, year, lang, cover, rights, description) or raise ValueError."""
    link = (link or "").strip()
    m = re.search(r"archive\.org/(?:details|embed|stream)/([A-Za-z0-9._-]+)", link)
    if m:
        ident = m.group(1); out = {"source": "archive", "source_id": ident, "source_url": "https://archive.org/details/" + ident, "cover": "https://archive.org/services/img/" + ident}
        try:
            md = (_json("https://archive.org/metadata/" + ident) or {}).get("metadata") or {}
        except Exception:
            md = {}
        if not md:
            raise ValueError("Internet Archive did not return that item. Check the link.")
        lang = str(_first(md.get("language"))).lower()
        desc = re.sub(r"<[^>]+>", " ", str(_first(md.get("description"))))
        out.update(title=str(_first(md.get("title")))[:200], author=str(_first(md.get("creator")))[:160], year=str(_first(md.get("date")) or _first(md.get("year")))[:12],
                   lang="ur" if lang.startswith(("urd", "ur")) else "ar" if lang.startswith(("ara", "ar")) else "en",
                   rights=str(_first(md.get("licenseurl")) or _first(md.get("rights")) or _first(md.get("possible-copyright-status")))[:200],
                   description=re.sub(r"\s+", " ", desc).strip()[:600])
        return out
    m = re.search(r"gutenberg\.org/(?:ebooks|cache/epub|files)/(\d+)", link)
    if m:
        n = m.group(1); out = {"source": "gutenberg", "source_id": n, "source_url": "https://www.gutenberg.org/ebooks/%s.html.images" % n,
                               "cover": "https://www.gutenberg.org/cache/epub/%s/pg%s.cover.medium.jpg" % (n, n), "rights": "Public domain in the USA (Project Gutenberg)"}
        try:
            g = _json("https://gutendex.com/books/" + n)
        except Exception:
            g = {}
        a = (g.get("authors") or [{}])[0]
        out.update(title=str(g.get("title") or "Project Gutenberg book %s" % n)[:200], author=str(a.get("name") or "")[:160],
                   year="", lang=(g.get("languages") or ["en"])[0][:2], description=", ".join(g.get("subjects") or [])[:600])
        return out
    m = re.search(r"([a-z]{2,3})\.wikisource\.org/wiki/([^?#]+)", link)
    if m:
        page = urllib.parse.unquote(m.group(2)); title = page.replace("_", " ")
        return {"source": "wikisource", "source_id": m.group(1) + ":" + page, "source_url": "https://%s.wikisource.org/wiki/%s" % (m.group(1), urllib.parse.quote(page)),
                "title": title[:200], "author": "", "year": "", "lang": "ur" if m.group(1) == "ur" else "ar" if m.group(1) == "ar" else "en",
                "cover": "", "rights": "Wikisource (public domain or free licence)", "description": ""}
    raise ValueError("Paste a link from archive.org, gutenberg.org or wikisource.org.")
