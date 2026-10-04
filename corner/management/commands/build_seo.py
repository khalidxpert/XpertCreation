"""Build Google-friendly static pages: recipes, surahs (Kanz-ul-Iman), MCQ topics, board notices, and sitemap-content.xml.
Usage: manage.py build_seo [--land DIR] [--surahs 1,112] (default: all 114)."""
import html
import json
import os
import re
import time
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

B = "https://xpertcreation.com"
E = lambda s: html.escape(str(s or ""), quote=True)


def _page(src, body, title, desc, path, jsonld=None):
    A_WRAP, A_BELL, A_HEAD = '<div class="wrap">', "<script>\n/* Bell:", "<b>Team</b></a>"
    s = re.sub(r"<title>.*?</title>", "<title>" + E(title) + "</title>", src, 1, re.S).replace(A_HEAD, "<b>" + E(title.split(" \u2014 ")[0][:40]) + "</b></a>", 1)
    s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + E(desc) + '">', s, 1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="' + B + path + '">', s, 1)
    s = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="' + E(title) + '">', s, 1)
    s = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="' + B + path + '">', s, 1)
    s = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="' + E(desc) + '">', s, 1)
    s = re.sub(r'<meta name="twitter:title" content="[^"]*">', '<meta name="twitter:title" content="' + E(title) + '">', s, 1)
    s = re.sub(r'<meta name="twitter:description" content="[^"]*">', '<meta name="twitter:description" content="' + E(desc) + '">', s, 1)
    if jsonld:
        s = s.replace("</head>", '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n</head>", 1)
    i, j = s.index(A_WRAP), s.index(A_BELL)
    return s[:i] + '<div class="wrap" style="max-width:820px">' + body + "</div>\n" + s[j:]


CSS = ('<style>.sx{background:var(--card,#fff);border:1px solid var(--line,#E4E8F2);border-radius:16px;padding:16px;margin:0 0 12px}.sx h2{font-size:18px;margin:0 0 8px}'
       '.sxm{color:var(--ink-soft,#5A657C);font-size:14px}.sxl a{display:inline-block;margin:4px 8px 4px 0;padding:7px 12px;border-radius:99px;background:var(--paper,#EEF1F6);text-decoration:none;font-weight:700;font-size:14px}'
       '.sxar{font-family:"Amiri","Noto Naskh Arabic","Traditional Arabic",serif;font-size:28px;line-height:2;direction:rtl;text-align:right;color:#0F3D2E}'
       '.sxur{direction:rtl;text-align:right;font-family:"Noto Nastaliq Urdu","Jameel Noori Nastaleeq",serif;font-size:19px;line-height:2.1;margin-top:6px}.sxen{line-height:1.6;margin-top:6px}'
       '.sxq li{margin:4px 0}.sxq details{margin-top:8px}.sxq summary{cursor:pointer;font-weight:800;color:#1B4DFF}</style>')


class Command(BaseCommand):
    help = "Build static SEO pages and sitemap-content.xml."

    def add_arguments(self, p):
        p.add_argument("--land", default="/var/www/xpertcreation-landing")
        p.add_argument("--surahs", default="")

    def w(self, path, text):
        full = os.path.join(self.land, path.lstrip("/") + ".html")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        old = open(full, encoding="utf-8").read() if os.path.exists(full) else None
        if old != text:
            open(full, "w", encoding="utf-8").write(text); self.changed += 1
        self.urls.append((path, date.fromtimestamp(os.path.getmtime(full)).isoformat()))

    def handle(self, *a, **o):
        self.land, self.urls, self.changed = o["land"], [], 0
        src = open(os.path.join(self.land, "team.html"), encoding="utf-8").read()
        self.recipes(src); self.quran(src, o["surahs"]); self.mcq(src); self.board(src); self.bus(src); self.library(src); self.afsanay(src)
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
            "  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>\n" % (B, p, d) for p, d in self.urls) + "</urlset>\n"
        open(os.path.join(self.land, "sitemap-content.xml"), "w").write(sm)
        self.stdout.write("seo pages: %d listed, %d changed" % (len(self.urls), self.changed))

    # ---- recipes
    def recipes(self, src):
        from corner.models import Recipe
        from corner.views import _seed
        _seed()
        rows = list(Recipe.objects.filter(approved=True).order_by("id")); seen = set(); keep = set()
        for r in rows:
            s = slugify(r.title) or "recipe"; s = s if s not in seen else "%s-%d" % (s, r.id); seen.add(s); r.slug_ = s
        for r in rows:
            img = (B + settings.MEDIA_URL.rstrip("/") + "/" + r.photo) if r.photo else ""
            imgs = [img] if img else self._card(r)
            img = img or (imgs[1] if imgs else "")
            ing = ["%s %s %s" % (("%g" % x[0]) if isinstance(x[0], (int, float)) else x[0], x[1], x[2]) for x in r.ingredients]
            by = (getattr(r.author, "full_name", "") or getattr(r.author, "username", "")) if r.author else "XpertCreation kitchen"
            ld = {"@context": "https://schema.org", "@type": "Recipe", "name": r.title, "description": r.intro or r.title, "recipeCuisine": "Pakistani",
                  "recipeCategory": r.category, "totalTime": "PT%dM" % r.minutes, "recipeYield": "%d servings" % r.serves, "recipeIngredient": ing,
                  "recipeInstructions": [{"@type": "HowToStep", "name": "Step %d" % (k + 1), "text": s, "url": B + "/recipes/" + r.slug_ + "#step-%d" % (k + 1)} for k, s in enumerate(r.steps)], "keywords": ", ".join(["Pakistani recipe", r.title, {"main": "main dish", "rice": "rice dish", "snack": "snack", "sweet": "dessert", "side": "side dish", "bread": "bread"}.get(r.category, r.category), "how to make " + r.title.lower()]), "author": {"@type": "Organization" if not r.author else "Person", "name": by},
                  "datePublished": r.created_at.date().isoformat()}
            if imgs: ld["image"] = imgs
            more = " ".join('<a href="/recipes/%s">%s</a>' % (x.slug_, E(x.title)) for x in rows if x.id != r.id)[:4000]
            body = (CSS + '<p class="sxm"><a href="/recipes">\u2190 All recipes</a></p>' + ('<img src="%s" alt="%s" style="width:100%%;max-height:380px;object-fit:cover;border-radius:16px">' % (E(img), E(r.title)) if img else "")
                    + '<h1 style="font-size:27px;margin:10px 0 4px">%s</h1><p class="sxm">%s</p><p>\u23F1 %d minutes \u00b7 serves %d \u00b7 by %s</p>' % (E(r.title), E(r.intro), r.minutes, r.serves, E(by))
                    + '<div class="sx"><h2>Ingredients</h2><ul>' + "".join("<li>%s</li>" % E(x) for x in ing) + "</ul></div>"
                    + '<div class="sx"><h2>Method</h2><ol>' + "".join('<li id="step-%d">%s</li>' % (k + 1, E(s)) for k, s in enumerate(r.steps)) + "</ol></div>"
                    + '<p><a href="/recipes?r=%d" style="font-weight:800">Change the number of servings \u2192</a></p><div class="sx sxl"><h2>More Pakistani recipes</h2>%s</div>' % (r.id, more))
            self.w("/recipes/" + r.slug_, _page(src, body, "%s recipe \u2014 easy Pakistani recipe | XpertCreation" % r.title,
                                                  "%s: %s Ingredients and step-by-step method, %d minutes, serves %d." % (r.title, r.intro, r.minutes, r.serves), "/recipes/" + r.slug_, ld))
            keep.add(r.slug_ + ".html")
        d = os.path.join(self.land, "recipes")
        for f in os.listdir(d) if os.path.isdir(d) else []:
            if f.endswith(".html") and f not in keep: os.remove(os.path.join(d, f))

    def _card(self, r):
        """A branded picture for a recipe without a photo, in the three shapes Google recommends."""
        from PIL import Image, ImageDraw, ImageFont
        C = {"main": ((176, 40, 59), (245, 166, 35)), "rice": ((19, 138, 114), (52, 211, 153)), "snack": ((234, 88, 12), (250, 204, 21)),
             "sweet": ((190, 24, 93), (249, 168, 212)), "side": ((22, 101, 52), (163, 230, 53)), "bread": ((146, 64, 14), (251, 191, 36))}.get(r.category, ((176, 40, 59), (245, 166, 35)))
        def font(sz, bold=True):
            for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
                if os.path.exists(f): return ImageFont.truetype(f, sz)
            return ImageFont.load_default()
        d = os.path.join(self.land, "recipes", "img"); os.makedirs(d, exist_ok=True); out = []
        for tag, (W, H) in (("1x1", (1200, 1200)), ("4x3", (1200, 900)), ("16x9", (1200, 675))):
            fn = os.path.join(d, "%s-%s.webp" % (r.slug_, tag))
            if not os.path.exists(fn):
                im = Image.new("RGB", (W, H)); px = ImageDraw.Draw(im)
                for y in range(H):
                    t = y / H; px.line([(0, y), (W, y)], fill=tuple(int(C[0][i] + (C[1][i] - C[0][i]) * t) for i in range(3)))
                px.rounded_rectangle((60, 60, W - 60, H - 60), radius=40, outline=(255, 255, 255), width=4)
                words, lines, f = r.title.split(), [], font(110)
                for w_ in words:
                    if lines and px.textlength(lines[-1] + " " + w_, font=f) < W - 200: lines[-1] += " " + w_
                    else: lines.append(w_)
                y = H // 2 - len(lines) * 65 - 40
                for ln in lines:
                    px.text((W // 2, y), ln, font=f, fill="white", anchor="mm"); y += 130
                px.text((W // 2, y + 10), "Pakistani recipe  \u00b7  %d min  \u00b7  serves %d" % (r.minutes, r.serves), font=font(44, False), fill=(255, 255, 255), anchor="mm")
                px.text((W // 2, H - 110), "xpertcreation.com/recipes", font=font(38), fill=(255, 255, 255), anchor="mm")
                im.save(fn, "WEBP", quality=85)
            out.append(B + "/recipes/img/%s-%s.webp" % (r.slug_, tag))
        return out

    # ---- quran
    def _surah(self, n):
        from corner.views import _get
        path = os.path.join(settings.MEDIA_ROOT, "quran", "%d.json" % n)
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
        ar, ur, en = _get("https://api.alquran.cloud/v1/surah/%d/editions/quran-uthmani,ur.kanzuliman,en.ahmedraza" % n)["data"]
        out = {"number": n, "name": ar["englishName"], "arabic_name": ar["name"], "meaning": ar.get("englishNameTranslation", ""),
               "ayahs": [{"n": x["numberInSurah"], "ar": x["text"], "ur": ur["ayahs"][i]["text"], "en": en["ayahs"][i]["text"]} for i, x in enumerate(ar["ayahs"])],
               "source": "Quran text and translations: AlQuran Cloud (Tanzil). Urdu: Kanz-ul-Iman by Imam Ahmed Raza Khan. English: translation of Kanz-ul-Iman."}
        os.makedirs(os.path.dirname(path), exist_ok=True); json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(0.3)
        return out

    def quran(self, src, only):
        nums = [int(x) for x in only.split(",") if x.strip()] or list(range(1, 115))
        got = {}
        for n in nums:
            try:
                got[n] = self._surah(n)
            except Exception as e:
                self.stderr.write("surah %d: %s" % (n, e))
        for f in os.listdir(os.path.join(settings.MEDIA_ROOT, "quran")) if os.path.isdir(os.path.join(settings.MEDIA_ROOT, "quran")) else []:
            m = re.match(r"(\d+)\.json$", f)
            if m and int(m.group(1)) not in got:
                got[int(m.group(1))] = json.load(open(os.path.join(settings.MEDIA_ROOT, "quran", f), encoding="utf-8"))
        slug = lambda d: "/quran/%d-%s" % (d["number"], slugify(d["name"]) or "surah")
        for n, d in sorted(got.items()):
            nav = ('<a href="%s">\u2190 %s</a> ' % (slug(got[n - 1]), E(got[n - 1]["name"])) if n - 1 in got else "") + '<a href="/quran">All surahs</a>' + (' <a href="%s">%s \u2192</a>' % (slug(got[n + 1]), E(got[n + 1]["name"])) if n + 1 in got else "")
            body = (CSS + '<p class="sxm sxl">' + nav + '</p><h1 style="font-size:26px;margin:8px 0 2px">Surah %s <span style="font-weight:400">(%s)</span></h1>' % (E(d["name"]), E(d["arabic_name"]))
                    + '<p class="sxm">%s \u00b7 %d ayahs \u00b7 Urdu translation Kanz-ul-Iman and English</p>' % (E(d.get("meaning", "")), len(d["ayahs"]))
                    + "".join('<div class="sx" id="a%d"><span class="sxm">%d:%d</span><div class="sxar">%s</div><div class="sxur">%s</div><div class="sxen">%s</div></div>' % (x["n"], n, x["n"], E(x["ar"]), E(x["ur"]), E(x["en"])) for x in d["ayahs"])
                    + '<p class="sxm sxl">' + nav + '</p><p class="sxm">%s</p>' % E(d["source"]))
            self.w(slug(d), _page(src, body, "Surah %s with Urdu translation (Kanz-ul-Iman) and English \u2014 XpertCreation" % d["name"],
                                  "Read Surah %s (%s) in Arabic with Urdu translation Kanz-ul-Iman and English, verse by verse. %d ayahs." % (d["name"], d["arabic_name"], len(d["ayahs"])), slug(d)))
        idx = CSS + '<h1 style="font-size:26px">\U0001F4D6 The Holy Quran with Urdu translation (Kanz-ul-Iman)</h1><div class="sx sxl">' + "".join('<a href="%s">%d. %s</a>' % (slug(d), n, E(d["name"])) for n, d in sorted(got.items())) + "</div>"
        self.w("/quran", _page(src, idx, "The Holy Quran with Urdu translation Kanz-ul-Iman \u2014 XpertCreation", "Read every surah of the Holy Quran in Arabic with Urdu translation Kanz-ul-Iman and English, verse by verse.", "/quran"))

    # ---- mcq topics
    def mcq(self, src):
        from mcq.views import CATS, Q
        SL = {"pak": "pakistan-affairs", "gk": "general-knowledge", "isl": "islamic-studies", "eng": "english", "sci": "everyday-science", "cs": "computer"}
        links = " ".join('<a href="/mcq/%s">%s</a>' % (SL[k], E(v)) for k, v in CATS.items())
        for k, name in CATS.items():
            qs = [q for q in Q if q["cat"] == k]
            body = (CSS + '<p class="sxm"><a href="/mcq">\u2190 Daily MCQs</a></p><h1 style="font-size:26px;margin:8px 0 4px">%s MCQs with answers</h1>' % E(name)
                    + '<p class="sxm">%d questions for PPSC, FPSC, CSS, NTS and MDCAT practice, each with the answer and a short explanation. <a href="/mcq">Take today\'s 10 \u2192</a></p>' % len(qs)
                    + "".join('<div class="sx sxq"><b>%d. %s</b><ol type="A">%s</ol><details><summary>Show answer</summary><p><b>%s. %s</b> \u2014 %s</p></details></div>'
                              % (i + 1, E(q["q"]), "".join("<li>%s</li>" % E(o) for o in q["o"]), "ABCD"[q["a"]], E(q["o"][q["a"]]), E(q["x"])) for i, q in enumerate(qs))
                    + '<div class="sx sxl"><h2>More topics</h2>' + links + "</div>")
            self.w("/mcq/" + SL[k], _page(src, body, "%s MCQs with answers for PPSC, FPSC, CSS and NTS \u2014 XpertCreation" % name,
                                          "%d %s MCQs with answers and explanations for PPSC, FPSC, CSS, NTS and MDCAT preparation." % (len(qs), name), "/mcq/" + SL[k]))

    # ---- board notices
    def board(self, src):
        from django.db.models import Q as DQ
        from notices.models import Notice
        rows = Notice.objects.filter(active=True).filter(DQ(last_date__isnull=True) | DQ(last_date__gte=timezone.localdate()))
        keep = set(); KIND = {"job": "Govt job", "result": "Result", "admission": "Admission", "scholarship": "Scholarship"}
        for n in rows:
            s = "%d-%s" % (n.id, slugify(n.title)[:60] or "notice")
            ld = None
            if n.kind == "job":
                ld = {"@context": "https://schema.org", "@type": "JobPosting", "title": n.title, "description": "<p>%s</p><p>Official notice: %s</p>" % (E(n.details or n.title), E(n.link)),
                      "datePosted": n.created_at.date().isoformat(), "hiringOrganization": {"@type": "Organization", "name": n.org or "Government of Pakistan"},
                      "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": n.city or "Pakistan", "addressCountry": "PK"}}, "directApply": False}
                if n.last_date: ld["validThrough"] = n.last_date.isoformat() + "T23:59"
            body = (CSS + '<p class="sxm"><a href="/board">\u2190 Jobs, results, admissions and scholarships</a></p><p class="sxm">%s</p><h1 style="font-size:25px;margin:4px 0">%s</h1>' % (KIND[n.kind], E(n.title))
                    + '<p class="sxm">%s</p>' % E(" \u00b7 ".join(x for x in (n.org, n.city, ("Last date: " + n.last_date.isoformat()) if n.last_date else "") if x))
                    + ('<div class="sx" style="white-space:pre-wrap">%s</div>' % E(n.details) if n.details else "")
                    + '<p><a href="%s" rel="noopener nofollow" style="display:inline-block;padding:11px 16px;border-radius:12px;background:#1B4DFF;color:#fff;font-weight:800;text-decoration:none">Open the official notice</a></p>' % E(n.link)
                    + '<p class="sxm">Always apply on the official website. XpertCreation never asks for fees to apply.</p>')
            self.w("/board/" + s, _page(src, body, "%s \u2014 %s | XpertCreation" % (n.title, n.org or KIND[n.kind]), "%s. %s %s" % (n.title, n.org, ("Last date " + n.last_date.isoformat()) if n.last_date else ""), "/board/" + s, ld))
            keep.add(s + ".html")
        d = os.path.join(self.land, "board")
        for f in os.listdir(d) if os.path.isdir(d) else []:
            if f.endswith(".html") and f not in keep: os.remove(os.path.join(d, f))

    # ---- bus terminal cities
    def bus(self, src):
        try:
            from bus.models import Terminal
        except Exception:
            return
        from collections import OrderedDict
        by = OrderedDict()
        for t in Terminal.objects.select_related("company").order_by("city", "company__name", "name"):
            by.setdefault(t.city, []).append(t)
        keep = set()
        for city, T in by.items():
            slug = slugify(city) or "city"; cards, ld = [], []
            for t in T:
                head, _, rest = t.name.partition(": "); addr, _, phone = rest.partition(" \u00b7 \u260E ")
                cards.append('<div class="sx"><b>%s</b> \u00b7 %s%s%s</div>' % (E(t.company.name), E(head), ("<br>" + E(addr)) if addr else "", ("<br>\u260E <a href=\"tel:%s\">%s</a>" % (E(re.sub(r"[^\d+]", "", phone)[:13]), E(phone))) if phone else ""))
                item = {"@type": "BusStation", "name": "%s %s" % (t.company.name, head), "address": {"@type": "PostalAddress", "streetAddress": addr or head, "addressLocality": city, "addressCountry": "PK"}}
                if phone: item["telephone"] = phone
                ld.append(item)
            body = (CSS + '<p class="sxm"><a href="/bus">\u2190 All bus terminals</a></p><h1 style="font-size:26px;margin:8px 0 4px">Bus terminals in %s</h1>' % E(city)
                    + '<p class="sxm">Daewoo and Niazi Express terminals in %s with address and phone number. <a href="/bus?city=%s">Open the map \u2192</a></p>' % (E(city), E(city)) + "".join(cards)
                    + '<p class="sxm">From the companies\u2019 official websites. Call the terminal to confirm times and fares before you travel.</p>')
            self.w("/bus/" + slug, _page(src, body, "Bus terminals in %s: Daewoo and Niazi address and phone \u2014 XpertCreation" % city,
                                         "Daewoo and Niazi Express bus terminals in %s: address, phone number and map." % city, "/bus/" + slug, {"@context": "https://schema.org", "@graph": ld}))
            keep.add(slug + ".html")
        self._clean("bus", keep)

    # ---- library books
    def library(self, src):
        try:
            from library.models import Book
        except Exception:
            return
        keep = set()
        for b in Book.objects.filter(active=True).order_by("id"):
            slug = "%d-%s" % (b.id, slugify(b.title)[:60] or "book")
            ld = {"@context": "https://schema.org", "@type": "Book", "name": b.title, "inLanguage": b.lang, "url": B + "/library/" + slug}
            if b.author: ld["author"] = {"@type": "Person", "name": b.author}
            if b.cover: ld["image"] = b.cover
            body = (CSS + '<p class="sxm"><a href="/library">\u2190 Library</a></p><div style="display:flex;gap:16px;flex-wrap:wrap">'
                    + ('<img src="%s" alt="" style="width:160px;border-radius:12px;box-shadow:0 6px 14px rgba(0,0,0,.12)">' % E(b.cover) if b.cover else "")
                    + '<div style="flex:1;min-width:220px"><h1 style="font-size:26px;margin:0 0 6px">%s</h1><p><b>%s</b>%s</p>' % (E(b.title), E(b.author), (" \u00b7 " + E(b.year)) if b.year else "")
                    + ('<p class="sxm">%s</p>' % E(b.description) if b.description else "")
                    + '<p><a href="/library?id=%d" style="display:inline-block;padding:11px 16px;border-radius:12px;background:#A16207;color:#fff;font-weight:800;text-decoration:none">\U0001F4D6 Read online free</a></p>' % b.id
                    + '<p class="sxm">Source: %s%s</p></div></div>' % ({"archive": "Internet Archive", "gutenberg": "Project Gutenberg", "wikisource": "Wikisource"}.get(b.source, b.source), (" \u00b7 " + E(b.rights)) if b.rights else ""))
            self.w("/library/" + slug, _page(src, body, "%s%s: read online free \u2014 XpertCreation Library" % (b.title, (" by " + b.author) if b.author else ""),
                                             ("Read %s%s online free. %s" % (b.title, (" by " + b.author) if b.author else "", b.description))[:300], "/library/" + slug, ld))
            keep.add(slug + ".html")
        self._clean("library", keep)

    # ---- afsanay (published, approved stories only)
    def afsanay(self, src):
        try:
            from afsanay.models import Afsana
        except Exception:
            return
        keep = set(); CATS = dict(Afsana.CATS)
        for a in Afsana.objects.filter(status="published", hidden=False).select_related("author").order_by("id"):
            q = a.qists.filter(approved=True).order_by("n").first()
            if not q:
                continue
            n = a.qists.filter(approved=True).count(); slug = "%d-%s" % (a.id, slugify(a.title)[:60] or "story")
            who = (getattr(a.author, "full_name", "") or "").strip() or getattr(a.author, "username", "") or "Writer"
            ur = ' class="ur"' if a.lang == "ur" else ""
            ld = {"@context": "https://schema.org", "@type": "ShortStory", "name": a.title, "inLanguage": a.lang, "genre": CATS.get(a.category, a.category),
                  "author": {"@type": "Person", "name": who}, "datePublished": a.created_at.date().isoformat(), "url": B + "/afsanay/" + slug}
            body = (CSS + '<style>.ur{direction:rtl;text-align:right;font-family:"Noto Nastaliq Urdu","Jameel Noori Nastaleeq",serif;line-height:2.2}</style>'
                    + '<p class="sxm"><a href="/afsanay">\u2190 Afsanay</a></p><h1%s style="font-size:26px;margin:8px 0 4px">%s</h1>' % (ur, E(a.title))
                    + '<p class="sxm">\u270D\uFE0F %s \u00b7 %s \u00b7 %d qist%s%s</p>' % (E(who), E(CATS.get(a.category, a.category)), n, "" if n == 1 else "s", " \u00b7 complete" if a.complete else "")
                    + ('<p%s>%s</p>' % (ur, E(a.summary)) if a.summary else "")
                    + '<div class="sx"><h2>Qist 1%s</h2><div%s style="white-space:pre-wrap;font-size:18px">%s</div></div>' % ((": " + E(q.title)) if q.title else "", ur, E(q.body))
                    + ('<p><a href="/afsanay?id=%d&q=2" style="display:inline-block;padding:11px 16px;border-radius:12px;background:#7C3AED;color:#fff;font-weight:800;text-decoration:none">Continue reading: Qist 2 \u2192</a></p>' % a.id if n > 1 else "")
                    + '<p><a href="/afsanay?id=%d">Like, save or comment on this story \u2192</a></p>' % a.id)
            self.w("/afsanay/" + slug, _page(src, body, "%s \u2014 %s by %s | Afsanay on XpertCreation" % (a.title, CATS.get(a.category, "story"), who),
                                             ("%s. %s" % (a.title, a.summary or q.body[:200]))[:300], "/afsanay/" + slug, ld))
            keep.add(slug + ".html")
        self._clean("afsanay", keep)

    def _clean(self, folder, keep):
        d = os.path.join(self.land, folder)
        for f in os.listdir(d) if os.path.isdir(d) else []:
            if f.endswith(".html") and f not in keep:
                os.remove(os.path.join(d, f))
