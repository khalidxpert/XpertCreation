#!/usr/bin/env python3
# The user guide at xpertcreation.com/docs - our own pages, same header and footer as the site.
# Builds /docs and /docs/<page> from the guide's GitHub repo (the one place it lives), adds a "Guide" footer link, nginx
# locations and sitemap entries.
#   python3 /root/docs_sync.py              pull the guide repo; rebuild /docs only if it changed
#   python3 /root/docs_sync.py --force      rebuild anyway
#   python3 /root/docs_sync.py --dry-run    build into /tmp/docspages only
import os, re, sys, glob, json, html, shutil, subprocess
from datetime import datetime

LAND = os.environ.get("LAND", "/var/www/xpertcreation-landing")
NGINX = os.environ.get("NGINX", "/etc/nginx/sites-enabled/xpertcreation-landing")
TEAM = LAND + "/team.html"
APPLY = "--dry-run" not in sys.argv
OUT = (LAND + "/docs") if APPLY else "/tmp/docspages"
REPO_DIR = os.environ.get("REPO_DIR", "/opt/xc-guide")
REPO_URL = os.environ.get("REPO_URL", "")
FORCE = "--force" in sys.argv


def git(*args):
    return subprocess.run(["git", "-C", REPO_DIR] + list(args), capture_output=True, text=True)


if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
    if not REPO_URL:
        sys.exit("No clone at %s yet. Run once with REPO_URL=https://github.com/<you>/<repo>.git" % REPO_DIR)
    r = subprocess.run(["git", "clone", "--depth", "1", REPO_URL, REPO_DIR], capture_output=True, text=True)
    if r.returncode:
        sys.exit("git clone failed: " + r.stderr[-300:])
    FORCE = True
before = git("rev-parse", "HEAD").stdout.strip()
r = git("pull", "--ff-only", "--quiet")
if r.returncode:
    sys.exit("git pull failed: " + r.stderr[-300:])
after = git("rev-parse", "HEAD").stdout.strip()
BUILT = "/root/.docs_built_commit"
last = open(BUILT).read().strip() if os.path.exists(BUILT) else ""
if last == after and not FORCE and os.path.exists(LAND + "/docs/index.html"):
    print("no change in the guide (%s) - nothing to do" % after[:7])
    sys.exit(0)
DOCS = {}
for root, dirs, files in os.walk(REPO_DIR):
    dirs[:] = [d for d in dirs if not d.startswith(".")]
    for f in files:
        if f.endswith(".md"):
            p = os.path.join(root, f)
            DOCS[os.path.relpath(p, REPO_DIR).replace(os.sep, "/")] = open(p, encoding="utf-8").read()
if "SUMMARY.md" not in DOCS or "README.md" not in DOCS:
    sys.exit("STOP - the repo needs README.md and SUMMARY.md at its top level. Nothing changed.")
print("guide commit %s, %d pages" % (after[:7], len(DOCS) - 1))

def slug(path):
    return "index" if path == "README.md" else path[:-3].replace("/", "-")

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
    def link(m):
        text, url = m.group(1), m.group(2)
        if url.endswith(".md") and not url.startswith("http"):
            u = "/docs" if url == "README.md" else "/docs/" + slug(os.path.normpath(url))
            return '<a href="%s">%s</a>' % (u, text)
        ext = url.startswith("http") and "xpertcreation.com" not in url
        return '<a href="%s"%s>%s</a>' % (url, ' target="_blank" rel="noopener"' if ext else "", text)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)

def md(src, here):
    out, para, lst = [], [], None
    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>"); para = []
        if lst:
            out.append("<%s>%s</%s>" % (lst[0], "".join("<li>%s</li>" % inline(x) for x in lst[1]), lst[0])); lst = None
    for line in src.splitlines():
        s = line.rstrip()
        # links inside this page's folder are relative to it
        s = re.sub(r"\]\(((?!http)[^)]+\.md)\)", lambda m: "](" + os.path.normpath(os.path.join(os.path.dirname(here), m.group(1))) + ")", s)
        h = re.match(r"^(#{1,3}) (.*)$", s)
        ul = re.match(r"^[-*] (.*)$", s)
        ol = re.match(r"^\d+\. (.*)$", s)
        if not s:
            flush()
        elif h:
            flush(); n = len(h.group(1)); out.append("<h%d>%s</h%d>" % (n, inline(h.group(2)), n))
        elif ul or ol:
            kind = "ul" if ul else "ol"
            if para: flush()
            if lst and lst[0] != kind: flush()
            if not lst: lst = [kind, []]
            lst[1].append((ul or ol).group(1))
        else:
            if lst: flush()
            para.append(s)
    flush()
    return "\n".join(out)

# Table of contents from SUMMARY.md
TOC, order = [], []
for line in DOCS["SUMMARY.md"].splitlines():
    g = re.match(r"^## (.*)$", line)
    it = re.match(r"^\* \[([^\]]+)\]\(([^)]+)\)$", line)
    if g: TOC.append([g.group(1), []])
    elif it:
        if not TOC: TOC.append(["", []])
        TOC[-1][1].append((it.group(1), it.group(2))); order.append(it.group(2))

def toc_html(cur):
    h = "<nav class='dtoc'>"
    for g, items in TOC:
        if g: h += "<b>%s</b>" % html.escape(g)
        for t, p in items:
            u = "/docs" if p == "README.md" else "/docs/" + slug(p)
            h += "<a href='%s'%s>%s</a>" % (u, " class='on'" if p == cur else "", html.escape(t))
    return h + "</nav>"

CSS = """<style>
.docs{display:grid;grid-template-columns:230px 1fr;gap:28px;align-items:start}
.dtoc{position:sticky;top:80px;display:flex;flex-direction:column;gap:2px;font-size:14px;max-height:calc(100vh - 100px);overflow:auto}
.dtoc b{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-soft,#5A657C);margin:14px 0 4px}
.dtoc a{padding:6px 10px;border-radius:9px;text-decoration:none;color:var(--ink,#0D1424)}
.dtoc a.on{background:var(--paper,#F6F7FB);font-weight:700;color:var(--brand,#1B4DFF)}
.dbody{min-width:0;line-height:1.7;font-size:15.5px}
.dbody h1{margin-top:0}.dbody h2{margin-top:28px}.dbody code{background:var(--paper,#F6F7FB);padding:1px 6px;border-radius:6px}
.dnav{display:flex;justify-content:space-between;gap:10px;margin-top:34px;padding-top:16px;border-top:1px solid var(--line,#E4E8F2)}
.dnav a{text-decoration:none;font-weight:700}
.dmenu{display:none}
@media(max-width:820px){.docs{grid-template-columns:1fr}.dtoc{position:static;display:none;max-height:none}
  .dtoc.open{display:flex}.dmenu{display:block;margin-bottom:10px;padding:9px 14px;border:1px solid var(--line,#E4E8F2);
  border-radius:11px;background:var(--card,#fff);font:inherit;font-weight:700}}
</style>"""

def page_body(path):
    i = order.index(path) if path in order else 0
    prev = order[i - 1] if i > 0 else None
    nxt = order[i + 1] if i + 1 < len(order) else None
    title = lambda p: [t for g, its in TOC for t, q in its if q == p][0]
    url = lambda p: "/docs" if p == "README.md" else "/docs/" + slug(p)
    nav = "<div class='dnav'><span>%s</span><span>%s</span></div>" % (
        "<a href='%s'>&larr; %s</a>" % (url(prev), html.escape(title(prev))) if prev else "",
        "<a href='%s'>%s &rarr;</a>" % (url(nxt), html.escape(title(nxt))) if nxt else "")
    return ('<div class="wrap">\n<button class="dmenu" onclick="this.nextElementSibling.querySelector(\'.dtoc\').classList.toggle(\'open\')">'
            '&#9776; Contents</button>\n<div class="docs">' + toc_html(path) + '<article class="dbody">'
            + md(DOCS[path], path) + nav + '</article></div>\n</div>\n' + CSS + "\n")

fail = []
def need(label, ok):
    print("  %-40s %s" % (label, "ok" if ok else "PROBLEM"))
    if not ok: fail.append(label)

src = open(TEAM, encoding="utf-8").read()
A_WRAP, A_BELL, A_HEAD = '<div class="wrap">', "<script>\n/* Bell:", "<b>Team</b></a>"
need("team.html template anchors", src.count(A_WRAP) == 1 and src.count(A_BELL) == 1 and src.count(A_HEAD) == 1)

def meta_sub(s, attr, name, value):
    return re.sub(r'(<meta %s="%s" content=")[^"]*(")' % (attr, re.escape(name)), lambda m: m.group(1) + value + m.group(2), s)

def build(path):
    text = DOCS[path]
    t = re.match(r"^# (.*)$", text, re.M).group(1)
    first = [l for l in text.splitlines() if l and not l.startswith("#")][0]
    desc = html.escape(re.sub(r"[*`\[\]]|\(http[^)]*\)|\([^)]*\.md\)", "", first)[:155], quote=True)
    url = "https://xpertcreation.com/docs" + ("" if path == "README.md" else "/" + slug(path))
    full = html.escape(t) + " \u2014 XpertCreation guide"
    s = src
    s = re.sub(r"<title>.*?</title>", lambda m: "<title>%s</title>" % full, s, 1, re.S)
    s = re.sub(r'<meta name="description" content="[^"]*">', lambda m: '<meta name="description" content="%s">' % desc, s, 1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', lambda m: '<link rel="canonical" href="%s">' % url, s, 1)
    for attr, name, val in (("property", "og:title", full), ("property", "og:description", desc), ("property", "og:url", url),
                            ("name", "twitter:title", full), ("name", "twitter:description", desc)):
        s = meta_sub(s, attr, name, val)
    ld = json.dumps({"@context": "https://schema.org", "@type": "TechArticle", "headline": t, "url": url,
                     "description": html.unescape(desc), "inLanguage": "en",
                     "publisher": {"@type": "Organization", "name": "XpertCreation", "url": "https://xpertcreation.com"}})
    s = re.sub(r'<script type="application/ld\+json">.*?</script>', lambda m: '<script type="application/ld+json">%s</script>' % ld, s, 1, re.S)
    s = s.replace(A_HEAD, "<b>Guide</b></a>", 1)
    i, j = s.index(A_WRAP), s.index(A_BELL)
    return s[:i] + page_body(path) + s[j:]

built = {}
if not fail:
    for path in DOCS:
        if path == "SUMMARY.md":
            continue
        built[slug(path) + ".html"] = build(path)
    need("pages built", len(built) >= 20)
    need("every summary page exists", all(p in DOCS for p in order))

print("footer link")
A_FOOT = '        <li><a href="/shows">Shows</a></li>\n'
foot = []
for f in sorted(glob.glob(LAND + "/*.html")):
    s = open(f, encoding="utf-8").read()
    if '<footer class="xcfoot">' in s and 'href="/docs"' not in s and s.count(A_FOOT) == 1:
        foot.append(f)
print("  footer pages to get a Guide link:", len(foot))
F_ADD = A_FOOT + '        <li><a href="/docs">Guide</a></li>\n'
built = {k: v.replace(A_FOOT, F_ADD, 1) if 'href="/docs"' not in v else v for k, v in built.items()}

print("nginx")
ng = open(NGINX).read()
i_ng, j_ng = ng.find("    location = /tools "), ng.find("listen 80;")
need("nginx anchor in the 443 block", "/docs/index.html" in ng or (i_ng != -1 and (j_ng == -1 or i_ng < j_ng)))
ng2 = ng
if i_ng != -1 and "/docs/index.html" not in ng:
    e = ng.index("\n", i_ng) + 1
    ng2 = ng[:e] + ("    location = /docs           { try_files /docs/index.html =404; }\n"
                    "    location ~ ^/docs/([a-z0-9-]+)/?$ { try_files /docs/$1.html =404; }\n") + ng[e:]

print("sitemap")
SM = LAND + "/sitemap.xml"
sm = open(SM, encoding="utf-8").read()
need("sitemap has </urlset>", "</urlset>" in sm)
urls = ["https://xpertcreation.com/docs" + ("" if k == "index.html" else "/" + k[:-5]) for k in built]
add = "".join("  <url><loc>%s</loc></url>\n" % u for u in urls if (u + "<") not in sm)
sm2 = sm.replace("</urlset>", add + "</urlset>", 1)

if fail:
    sys.exit("\nSTOP - " + ", ".join(fail) + ". Nothing written.")
if not APPLY:
    os.makedirs(OUT, exist_ok=True)
    for k, v in built.items():
        open(os.path.join(OUT, k), "w", encoding="utf-8").write(v)
    print("\nDRY RUN OK - %d pages in /tmp/docspages, nothing live changed. Run again with --apply." % len(built))
    sys.exit(0)

bak = "/root/docs_bak_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
os.makedirs(bak, exist_ok=True)
# the guide itself lives in git; keep only the five newest backups of what this script touches
for old_bak in sorted(glob.glob("/root/docs_bak_*"))[:-5]:
    shutil.rmtree(old_bak, ignore_errors=True)
shutil.copy(NGINX, os.path.join(bak, "nginx_xpertcreation-landing"))
shutil.copy(SM, bak)
for f in foot:
    shutil.copy(f, bak)
open("/tmp/docs_bakdir", "w").write(bak)
if os.path.isdir(OUT):
    shutil.move(OUT, os.path.join(bak, "docs_old"))
os.makedirs(OUT)
for k, v in built.items():
    open(os.path.join(OUT, k), "w", encoding="utf-8").write(v)
for f in foot:
    s = open(f, encoding="utf-8").read()
    open(f, "w", encoding="utf-8").write(s.replace(A_FOOT, F_ADD, 1))
open(SM, "w", encoding="utf-8").write(sm2)
if ng2 != ng:
    open(NGINX, "w").write(ng2)
    open("/tmp/docs_nginx_changed", "w").write("1")
try:
    for f in os.listdir(OUT): shutil.chown(os.path.join(OUT, f), "www-data", "www-data")
    shutil.chown(OUT, "www-data", "www-data")
except Exception:
    pass
print("\nAPPLIED - %d pages, %d footer links, %d sitemap urls. Backups in %s" % (len(built), len(foot), add.count("<url>"), bak))
if APPLY:
    open(BUILT, "w").write(after)
