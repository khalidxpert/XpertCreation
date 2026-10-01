"""Posts from the official XpertCreation account: to the Connect feed and, through the bot, to the
XpertCreation group. Sources: the tool pages, Shows (TMDB lists), the news feeds and the sports data."""
import glob
import html
import os
import random
import re
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve
from django.utils import timezone

from .models import AutoPost, OfficialAdded

User = get_user_model()
OFFICIAL_EMAIL = "khalid@xpertcreation.com"            # daily posts come from Khalid (@khalidxpert)
GROUP_ID = 1
SITE = "https://xpertcreation.com"
LAND = "/var/www/xpertcreation-landing"
_rf = RequestFactory()


def official():
    u = User.objects.filter(email=OFFICIAL_EMAIL).first()
    if u:
        return u
    u = User.objects.create_user(email=OFFICIAL_EMAIL, password=None) if User.USERNAME_FIELD == "email" else User.objects.create_user(username="xpertcreation", email=OFFICIAL_EMAIL)
    for k, v in (("full_name", "XpertCreation"), ("is_email_verified", True), ("hide_from_leaderboard", True)):
        if hasattr(u, k):
            setattr(u, k, v)
    u.set_unusable_password()
    u.save()
    return u


def group():
    from notifications.models import ChatGroup
    return ChatGroup.objects.filter(id=GROUP_ID).first()


def add_to_official_group(user, welcome=True):
    from notifications.models import GroupMember
    g = group()
    if not g or OfficialAdded.objects.filter(user_id=user.id).exists():
        return False                       # added once already: if they left, we respect that
    OfficialAdded.objects.create(user_id=user.id)
    if GroupMember.objects.filter(group=g, user=user).exists():
        return False
    try:
        from notifications.groupbot import banned, greet
        if banned(g, user):
            return False
    except Exception:
        greet = None
    GroupMember.objects.create(group=g, user=user)
    if welcome and greet and user.email != OFFICIAL_EMAIL:
        greet(g, user)
    return True


def _api(path):
    try:
        m = resolve(path.split("?")[0])          # the view lookup takes no ?query; the request below keeps it
        req = _rf.get(path, HTTP_HOST="xpertcreation.com", secure=True)
        req.user = AnonymousUser()
        r = m.func(req, *m.args, **m.kwargs)
        return r.data if getattr(r, "status_code", 500) == 200 else None
    except Exception:
        return None


def tools():
    """Every tool page: its address, title and description (read from the pages themselves)."""
    out = []
    for f in sorted(glob.glob(LAND + "/tools-pages/*.html")):
        s = open(f, encoding="utf-8", errors="ignore").read()
        t = re.search(r"<title>(.*?)</title>", s, re.S)
        d = re.search(r'<meta name="description" content="([^"]*)"', s)
        slug = os.path.basename(f)[:-5]
        title = html.unescape(t.group(1).strip()) if t else slug
        out.append({"slug": slug, "url": SITE + "/tools/" + slug, "title": re.split(r"\s+[\u2014|-]\s+XpertCreation", title)[0].strip(),
                    "desc": html.unescape(d.group(1)) if d else ""})
    return out


def _tag(s):
    """Whole words only, up to about 22 letters: #NumberToWordsConverter, never #NumberToWordsConverterForChequ."""
    out = ""
    for w in re.findall(r"[A-Za-z0-9]+", s):
        if out and len(out) + len(w) > 22:
            break
        out += w[:1].upper() + w[1:]
    return "#" + (out[:30] or "XpertCreation")


def _save_poster(url, owner_id):
    """Keep a copy of a TMDB poster as WebP in the feed's own folder."""
    try:
        import io
        import requests
        from PIL import Image
        r = requests.get(url.replace("/w342/", "/w500/"), timeout=15)
        if r.status_code != 200 or len(r.content) > 5_000_000:
            return None
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((1000, 1000))
        rel = "feed/%d/%s.webp" % (owner_id, secrets.token_hex(12))
        full = os.path.join(settings.MEDIA_ROOT, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        im.save(full, "WEBP", quality=80)
        return rel
    except Exception:
        return None


def _publish(kind, key, text, group_text=None, images=None):
    """One post to the feed and one message from Khalid in the group; skipped if this item was posted before."""
    if AutoPost.objects.filter(kind=kind, key=key).exists():
        return None
    from feed.models import Post
    u = official()
    p = Post.objects.create(author=u, body=text[:3000], images=images or [], visibility="public")
    g = group()
    if g:
        try:
            from django.db.models import F
            from django.utils import timezone
            from notifications.models import ChatGroup, GroupMember, GroupMessage
            if GroupMember.objects.filter(group=g, user=u).exists():      # posted by Khalid, not the bot
                GroupMessage.objects.create(group=g, author=u, body=(group_text or text)[:2000])
                ChatGroup.objects.filter(pk=g.pk).update(updated_at=timezone.now())
                GroupMember.objects.filter(group=g, user=u).update(msg_count=F("msg_count") + 1)
            else:
                from notifications.groupbot import say
                say(g, (group_text or text)[:2000])
        except Exception:
            pass
    AutoPost.objects.create(kind=kind, key=key[:200], text=text[:3000], feed_post_id=p.id)
    return p


def post_tool():
    done = set(AutoPost.objects.filter(kind="tool").values_list("key", flat=True))
    all_t = tools()
    fresh = [t for t in all_t if t["slug"] not in done]
    if not fresh:                                    # every tool posted once: start again, oldest first
        AutoPost.objects.filter(kind="tool").delete()
        fresh = all_t
    if not fresh:
        return None
    t = random.choice(fresh)
    tags = " ".join(["#XpertCreation", "#FreeTools", _tag(t["title"]), "#Pakistan"])
    text = "\U0001F9F0 %s\n\n%s\n\nFree, no sign-up, works on your phone:\n%s\n\n%s" % (t["title"], t["desc"], t["url"], tags)
    return _publish("tool", t["slug"], text)


def post_drama():
    done = set(AutoPost.objects.filter(kind="drama").values_list("key", flat=True))
    lists = ["pk_tv", "in_tv", "pk_movie", "in_movie"]
    random.shuffle(lists)
    for name in lists:
        d = _api("/api/screen/lists/%s/" % name) or {}
        for it in d.get("results") or []:
            key = "%s-%s" % (it.get("kind"), it.get("id"))
            if key in done or not it.get("overview"):
                continue
            what = "drama" if it.get("kind") == "tv" else "film"
            url = "%s/show/%s-%s" % (SITE, it.get("kind"), it.get("id"))
            tags = " ".join(["#XpertCreation", "#PakistaniDrama" if name == "pk_tv" else "#IndianDrama" if name == "in_tv" else "#Movies",
                             _tag(it.get("title") or ""), "#WhatToWatch"])
            text = "\U0001F3AC %s (%s) \u2014 today's %s pick\n\n%s\n\n\u2B50 %s/10 \u00b7 story, cast, trailer and where to watch:\n%s\n\n%s" % (
                it.get("title"), it.get("year") or "", what, (it.get("overview") or "")[:500], it.get("rating") or "\u2014", url, tags)
            u = official()
            img = _save_poster(it["poster"], u.id) if it.get("poster") else None
            return _publish("drama", key, text, images=[img] if img else [])
    return None


def post_news():
    done = set(AutoPost.objects.filter(kind="news").values_list("key", flat=True))
    for region in ("pk", "world"):
        d = _api("/api/news/?region=%s" % region) or {}
        for it in d.get("items") or []:
            if not it.get("link") or it["link"] in done:
                continue
            tags = "#XpertCreation #News #Pakistan" if region == "pk" else "#XpertCreation #WorldNews"
            text = "\U0001F4F0 %s\n\n%s\n\nSource: %s \u2014 read the full story:\n%s\n\nMore headlines: %s/news\n\n%s" % (
                it.get("title"), (it.get("summary") or "")[:400], it.get("source") or "", it["link"], SITE, tags)
            return _publish("news", it["link"], text)
    return None


def post_sports():
    today = str(timezone.localdate())
    if AutoPost.objects.filter(kind="sports", key__startswith=today).exists():
        return None
    c = _api("/api/sports/cricket/") or {}
    f = _api("/api/sports/football/") or {}
    lines = []
    for m in (c.get("live") or [])[:3]:
        sc = " | ".join("%s %s/%s (%s)" % (s.get("inning", "").replace(" Inning 1", "").replace(" Inning 2", ""), s.get("r"), s.get("w"), s.get("o")) for s in m.get("score") or [])
        lines.append("\U0001F3CF LIVE: %s\n   %s\n   %s" % (m.get("name"), sc or "", m.get("status") or ""))
    for m in (c.get("results") or [])[:2]:
        lines.append("\U0001F3CF %s \u2014 %s" % (m.get("name"), m.get("status")))
    soon = [m for m in (f.get("upcoming") or []) if (m.get("date") or "")[:10] <= str(timezone.localdate() + timezone.timedelta(days=2))][:4]
    for m in soon:
        lines.append("\u26BD %s v %s \u00b7 %s" % (m["home"]["name"], m["away"]["name"], m["comp"]["name"]))
    for m in (f.get("results") or [])[:2]:
        lines.append("\u26BD %s %s\u2013%s %s \u00b7 %s" % (m["home"]["name"], m["score"]["home"], m["score"]["away"], m["away"]["name"], m["comp"]["name"]))
    if not lines:
        return None
    text = "\U0001F3C6 Today in sports\n\n%s\n\nLive scores, scorecards and tables:\n%s/sports\n\n#XpertCreation #Cricket #Football #Sports #Pakistan" % ("\n\n".join(lines), SITE)
    return _publish("sports", today, text)


def catalogue_markdown():
    """The tools catalogue: every tool with its purpose and how to use it."""
    ts = tools()
    out = ["# XpertCreation tools catalogue", "", "%d free tools. Each opens on its own page, works on a phone, needs no sign-up, "
           "and does its work on the device (nothing typed is sent to us)." % len(ts), ""]
    for t in ts:
        out += ["## %s" % t["title"], "", "- **Purpose:** %s" % (t["desc"] or t["title"]),
                "- **How it works:** open the page, fill in the boxes, tap the button - the answer appears straight away. You can share the page from the share bar.",
                "- **Link:** %s" % t["url"], ""]
    return "\n".join(out)
