#!/usr/bin/env python3
# The user guide at xpertcreation.com/docs - our own pages, same header and footer as the site.
# Builds /docs and /docs/<page> from the Markdown below, adds a "Guide" footer link, nginx
# locations and sitemap entries.
#   python3 /root/gen_docs.py            dry run -> /tmp/docspages
#   python3 /root/gen_docs.py --apply    write
import os, re, sys, glob, json, html, shutil, subprocess
from datetime import datetime

LAND = os.environ.get("LAND", "/var/www/xpertcreation-landing")
NGINX = os.environ.get("NGINX", "/etc/nginx/sites-enabled/xpertcreation-landing")
TEAM = LAND + "/team.html"
APPLY = "--apply" in sys.argv
OUT = (LAND + "/docs") if APPLY else "/tmp/docspages"
DOCS = {
"SUMMARY.md": "# Summary\n\n* [XpertCreation guide](README.md)\n\n## Getting started\n* [Your account](start/account.md)\n* [The home page](start/home.md)\n* [Privacy and safety](start/privacy.md)\n\n## Learn\n* [XpertAcademy](learn/academy.md)\n* [Certificates and badges](learn/certificates.md)\n\n## Tools\n* [Everyday tools](tools/tools.md)\n* [Islamic tools](tools/islamic.md)\n* [Star signs and the real sky](tools/zodiac.md)\n\n## Connect\n* [Your professional profile](people/profile.md)\n* [Connect, follow and endorse](people/connect.md)\n* [The blue tick](people/blue-tick.md)\n\n## Pets\n* [My pets](pets/my-pets.md)\n* [The QR tag](pets/qr-tag.md)\n* [Lost and found](pets/lost-found.md)\n\n## Shows\n* [Dramas and films](shows/shows.md)\n\n## Games\n* [Games and points](games/games.md)\n* [Online chess](games/chess.md)\n\n## Community\n* [Blood bank](community/blood-bank.md)\n* [Donate](community/donate.md)\n* [Chat](community/chat.md)\n* [Birthdays, news and weather](community/more.md)\n\n## Help\n* [Getting help](help/support.md)\n* [Frequently asked questions](help/faq.md)\n",
"README.md": "# XpertCreation guide\n\nXpertCreation is a free platform from Lahore. Learn Microsoft Office, programming and languages, use more than seventy everyday tools, play games, find a blood donor, look after your pets, meet other members and keep up with Pakistani and Indian dramas and films.\n\nEverything on the site is free. There is nothing to buy.\n\nThis guide explains each part of the site and how to use it. Start with [Your account](start/account.md) if you are new.\n\n**Website:** [xpertcreation.com](https://xpertcreation.com)\n**Help:** [xpertcreation.com/support](https://xpertcreation.com/support)\n",
"community/donate.md": "# Donate\n\nAt [xpertcreation.com/donate](https://xpertcreation.com/donate). Give things you no longer need to people who can use them, or ask for something. When a donation request is accepted, the two of you can chat.\n",
"community/chat.md": "# Chat\n\nAt [xpertcreation.com/chat](https://xpertcreation.com/chat). Chat opens only between people who have agreed to something: an accepted connection, a blood request or a donation. Nobody can message you out of the blue.\n",
"community/more.md": "# Birthdays, news and weather\n\n- **Birthdays:** reminders for the birthdays you care about, every year.\n- **News:** the latest headlines.\n- **Weather:** today and the days ahead, where you are.\n- **Money:** cash, wallets and bank balances in one place, kept on your phone only.\n- **Visiting card:** your own digital card with a QR code, ready to share.\n- **Vibe check:** today's mood, from one question.\n",
"community/blood-bank.md": "# Blood bank\n\nAt [xpertcreation.com/blood](https://xpertcreation.com/blood). Find donors by blood group and city, sign up as a donor, and post a request when someone needs blood. When a donor accepts a request, you can chat with each other.\n",
"shows/shows.md": "# Dramas and films\n\nAt [xpertcreation.com/shows](https://xpertcreation.com/shows).\n\n## Browsing\nTabs for Pakistani dramas, Indian dramas, Pakistani films, Indian films and what is trending this week, or search by name.\n\n## A drama or film page\nThe story, cast, genres, seasons and episodes, the trailer, where to watch it in Pakistan, and ratings from TMDB and from our members. Where a channel posts the episodes itself, there is a button to watch them on its official YouTube channel.\n\n## Your list and your reviews\nPress **Add to my list** to keep a list of what you want to watch. Rate from one to five stars and write a few words if you like. One review per person per title.\n\nWe only link to official channels, never to copies.\n\nFilm and drama information and images come from TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB.\n",
"start/account.md": "# Your account\n\n## Creating an account\n1. Open [xpertcreation.com/register](https://xpertcreation.com/register).\n2. Enter your name, email address and a password.\n3. We send a code to your email. Enter it to verify your address.\n\nSome things need a verified email: posting on the lost & found board, endorsing people, sending connection requests and writing reviews. This keeps fake accounts out.\n\n## Your account page\nAt [xpertcreation.com/account](https://xpertcreation.com/account) you can:\n- change your name and password\n- choose an avatar or upload a photo\n- add your birthday (it fills in the age calculator and your star sign by itself)\n- add a WhatsApp number\n- change your privacy settings\n- open **Social links** to add your Facebook, Instagram, X and other accounts to your profile\n\n## Deleting your account\nGo to [xpertcreation.com/account/delete](https://xpertcreation.com/account/delete). Deleting removes your account and what belongs to it. It cannot be undone.\n",
"start/privacy.md": "# Privacy and safety\n\n## What other people can see\n- **Country counts** are public: how many members are in each country.\n- **Newest members** appear in the footer with a first name and an initial, for example \"Khalid S.\".\n- **Moderators** can see which members are online.\n- Your **professional profile** is visible to signed-in members by default. You can make it public (and findable on Google) or hide it completely.\n\nYou can hide your name from the public lists in your privacy settings.\n\n## What nobody else sees\nYour email address and your password are never shown to anyone. Your pets' health records are yours alone.\n\n## Chat is not open to strangers\nNobody can start a chat with you out of the blue. A chat opens only after you have agreed to something: accepting a connection request, a blood request or a donation.\n\n## Reporting\nProfiles, reviews and posts can be reported. Moderators look at every report.\n",
"start/home.md": "# The home page\n\nWhen you are signed in, the home page greets you by name with your country's flag, the time and date, and a few quick links.\n\n## Profile completion\nIf your professional profile is not finished, a box shows how complete it is and what is missing: a photo, a headline, your city, a few lines about you, three skills, a job and your education. Each item takes you to the right place. Press **Later** to hide it for three days.\n\n## The tiles\nEach tile opens a part of the site: Academy, Donate, Blood Bank, Games, News, Tools, Money, Connect, Pets, Shows, Birthdays, Chat and Support. The tiles follow the language you choose.\n\n## Where our members are\nNear the bottom you can see how many members there are, in which countries, and how many are online right now.\n\n## The footer\nEvery page ends with the same footer: our address, WhatsApp, email, links to the main sections, and a live strip of members who joined recently.\n\n## Account and profile\nYour account and your professional profile are one place with two tabs at the top: **Account** and **Professional profile**.\n",
"tools/zodiac.md": "# Star signs and the real sky\n\nAt [xpertcreation.com/zodiac](https://xpertcreation.com/zodiac).\n\n## The real sky\nToday's Moon phase, how much of it is lit, the next full and new moon, and which sign the Sun, Moon, Mercury, Venus, Mars, Jupiter and Saturn are in. These positions are real astronomy, worked out on your device.\n\n## Your Sun, Moon and Rising sign\nEnter your date of birth, the time if you know it, and where you were born. Without a time you still get your Sun sign. The Rising sign needs the time. If your birthday is on your account, it fills in by itself.\n\nStar signs are tradition and entertainment, not science. Please do not use them to make real decisions.\n",
"tools/tools.md": "# Everyday tools\n\nMore than seventy free tools at [xpertcreation.com/tools](https://xpertcreation.com/tools). Every tool also has its own page, for example [xpertcreation.com/tools/age-calculator](https://xpertcreation.com/tools/age-calculator).\n\n## Groups\n- **Money:** loan and EMI, FBR salary tax, electricity bill, zakat, GST, discount, profit margin, interest, salary converter, split the bill\n- **Convert:** length, weight (including tola, maund and seer), area (marla and kanal), volume, speed, temperature, clothing sizes, download time\n- **Dates:** age, days between dates, working days, countdown, add days to a date, time in two places, timer\n- **Maths:** scientific calculator, percentage, GPA and CGPA, admission aggregate, average\n- **Health:** BMI, ideal weight, body fat, due date, water a day\n- **Text:** word counter, change case, number to words, text cleaner, QR code, password maker\n- **Daily:** prayer times, Qibla direction, tasbeeh counter, WhatsApp link, passport photo, world clock, visiting card\n- **Developer:** JSON, Base64, URL encode, hash, UUID, regex tester, colour converter, cron, epoch time, slug maker\n\n## Filled in for you\nIf your birthday is on your account, the **age calculator** shows your age as soon as it opens. You can still change the date to check someone else's.\n",
"tools/islamic.md": "# Islamic tools\n\n## Prayer times\nNamaz times for where you are. Choose the calculation method (Karachi is the one most followed in Pakistan and India) and Hanafi or standard Asr.\n\n## Qibla direction\nPress **Use my location** to get the Qibla in degrees from North and the distance to the Kaaba. On a phone, press **Start compass** and hold the phone flat: the green arrow turns with you and says when you are facing the Qibla. A compass can be thrown off by metal nearby.\n\n## Hijri date converter\nEnglish date to Hijri, and back. It uses the Umm al-Qura calendar. In Pakistan the date follows moon sighting, so it can differ by a day.\n\n## Tasbeeh counter\nA big button to count your dhikr, with a target of 33, 99, 100 or 1000. The phone vibrates at the target and the count stays on your phone.\n\n## Zakat\nWorks out 2.5% of your zakatable wealth.\n",
"learn/certificates.md": "# Certificates and badges\n\n## Getting a certificate\n1. Finish the course and pass its quiz.\n2. Leave a short review of the course.\n3. Your certificate opens. Share it, or ask your friends to join.\n\n## Checking a certificate\nAnyone can check that a certificate is real at [xpertcreation.com/verify](https://xpertcreation.com/verify).\n\n## Badges and roles\nAs you learn you earn roles (Learner, Scholar, Content Creator, Mentor) and medals in seven areas, each with four tiers. Your role appears on the Academy home page.\n",
"learn/academy.md": "# XpertAcademy\n\nXpertAcademy has free courses at [xpertcreation.com/academy](https://xpertcreation.com/academy/).\n\n## Courses\n- **Microsoft Office:** Word, Excel, PowerPoint, VBA\n- **Programming:** Python, JavaScript\n- **Languages:** Korean, Turkish, German, French, Japanese\n- **Quran:** Al-Quran\n\n## How lessons work\nEach course is a series of lessons. You can link straight to a lesson, for example `/academy/?c=python&l=3`.\n\nIn the programming courses some lessons contain code you can **run in the page**: HTML, JavaScript and Python. Python loads once (about 6 MB) and then runs on your own device.\n\nIn the language courses, tap words in Korean, Japanese, Chinese or Arabic script to hear them spoken.\n\n## Community videos\nMembers can suggest YouTube or Vimeo videos for a course. They are checked before they appear.\n",
"help/support.md": "# Getting help\n\n- **Support tickets:** [xpertcreation.com/support](https://xpertcreation.com/support)\n- **WhatsApp:** +92 300 946 2916\n- **Email:** khalid@xpertcreation.com\n- **Facebook group:** linked in the footer of every page\n\nSuggestions and problem reports from the home page go straight to the CEO. Every message is read.\n",
"help/faq.md": "# Frequently asked questions\n\n**Is it really free?**\nYes. Everything on the site is free.\n\n**The site looks old after an update.**\nClose the app or tab and open it again. If it still looks old, clear the site's data in your browser settings.\n\n**Why can't I message someone?**\nChat opens only after you are connected, or after a blood or donation request is accepted.\n\n**Why is my profile not in Connect?**\nAdd a headline, make sure your email is verified, and check that your profile is not set to \"Only me\".\n\n**How do I get the blue tick?**\nAdmins and moderators have it. Everyone else can apply at 1,000 followers.\n\n**Someone found my pet. How will I know?**\nYou get a notification as soon as they leave a note on your pet's tag page.\n",
"games/games.md": "# Games and points\n\nThirteen games at [xpertcreation.com/games](https://xpertcreation.com/games), including chess, Ludo, sudoku, minesweeper, snake, 2048, Connect Four, Simon, a word game, tic-tac-toe and memory match.\n\n## Points\nPoints come from two games only:\n- **Memory match:** 1,000 × the best possible moves ÷ your moves, higher on medium and hard\n- **Tic-tac-toe against the computer:** win 100, draw 40, lose 10; ×2 on medium and ×4 on hard\n\nThe other games run in your browser and send nothing, so they do not add points.\n",
"games/chess.md": "# Online chess\n\n## Playing a friend\nPress **Play a friend** and send your friend the room code. They enter it and press **Join**. You can see whether the other player is still at the board.\n\n## Watching\nThe chess page lists games being played right now. Press **Watch** to follow one live. Watchers cannot move.\n",
"pets/my-pets.md": "# My pets\n\nAt [xpertcreation.com/pets](https://xpertcreation.com/pets).\n\n## Adding a pet\nPress **Add a pet** and fill in the name, kind (dog, cat, bird, rabbit, other), breed, gender, birthday and, if you want, a phone number to show on the tag. Add a photo afterwards (JPG, PNG or WebP, up to 2 MB).\n\n## Health records\nAdd vaccines, check-ups, deworming, medicine and weight, each with a date and, if needed, the next due date.\n\n## The vaccine schedule\nPress **Plan vaccines from the schedule**. Using your pet's birthday, the upcoming vaccines for its kind are added as *planned*. When one is given, press **Done**; if it repeats, the next one is planned for you.\n\n## Reminders\nEvery morning at 9 we check what is due in the next three days and send you a notification. Each date is reminded once. The **Coming up** box shows what is due in the next month, and anything overdue.\n",
"pets/qr-tag.md": "# The QR tag\n\nEvery pet gets a code and a QR tag. Print it from the pet's page and put it on the collar.\n\n## When someone finds your pet\nThey scan the tag and see your pet's photo and name. If you added a phone number, they can call you or send a WhatsApp message.\n\nThey can also leave a note, even without an account. You get a notification at once, and the note is saved on your pet's page.\n\n## Lost mode\nPress **Mark as lost**. Anyone who scans the tag sees that your pet is lost. When it is home, press the button again.\n",
"pets/lost-found.md": "# Lost and found\n\nAt [xpertcreation.com/lost](https://xpertcreation.com/lost). Anyone can look; you need a verified account to post.\n\n## Posting\nSay whether the pet is lost or found, its kind, a short title, the city and where exactly, a few details and, if you want, a phone number. You can add a photo afterwards. If it is one of your own pets, choose it and it is marked as lost too.\n\n## When it is sorted\nPress **Resolved** to take the post down. Posts close by themselves after sixty days.\n\nAdoption on XpertCreation is always free. We never allow pets to be sold here.\n",
"people/connect.md": "# Connect, follow and endorse\n\n## Connect\nPress **Connect** on someone's profile. They get a notification and can accept or decline. Once they accept, a **Message** button appears and you can chat.\n\nTo keep things friendly: up to thirty requests a day, and after a request is declined you can ask again only after thirty days.\n\n## Your lists\nOn your profile page, tap **followers**, **following** or **connections** to see the people. Each connection has a **Message** button.\n\n## Follow\nFollowing is one-way and needs nobody's approval. Your profile shows your followers, who you follow and your connections.\n\n## Endorse\nIf you know someone is good at something, press **Endorse** next to that skill. You can endorse each skill once, and never your own. The person gets a notification.\n\n## Report\nIf a profile is fake, spam or abusive, press **Report**. A moderator will look at it.\n",
"people/blue-tick.md": "# The blue tick\n\nThe blue tick shows a trusted member.\n\n- **Admins and moderators** have it automatically.\n- **Anyone else** can apply once they have **1,000 followers**. Only verified, active members count as followers.\n- Each request is checked by hand. You get a notification with the answer.\n\nThe blue tick is free. It cannot be bought.\n",
"people/profile.md": "# Your professional profile\n\nBuild it at [xpertcreation.com/me/profile](https://xpertcreation.com/me/profile). Your address will look like `xpertcreation.com/in/your-name`.\n\n## What to fill in\n- **Headline:** one line about what you do, for example \"Excel trainer and VBA developer\"\n- **Where you live:** pick your country (with its flag), then your state or province, then your city, all from lists\n- **About:** a few lines about yourself\n- **Open to work:** tick it and say what kind of work\n- **Links:** your website, and your social links: Facebook, Instagram, X, TikTok, YouTube, LinkedIn, GitHub, WhatsApp and many more. Type just your username\n- **Skills:** start typing and pick from the list, so everyone uses the same names\n- **Experience:** your jobs, with dates\n- **Education:** schools, colleges and universities\n\n## Who can see it\n- **Everyone, and Google**\n- **Signed-in members** (the default)\n- **Only me**\n\nA preview at the top of the page shows the card other members will see, and it changes as you type.\n\nFind other members in **Connect** at [xpertcreation.com/people](https://xpertcreation.com/people) by name, skill or city.\n"
}

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
need("nginx anchor in the 443 block", i_ng != -1 and (j_ng == -1 or i_ng < j_ng))
need("nginx has no /docs yet", "/docs/index.html" not in ng)
ng2 = ng
if i_ng != -1:
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

bak = "/root/docs_bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs(bak)
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
open(NGINX, "w").write(ng2)
try:
    for f in os.listdir(OUT): shutil.chown(os.path.join(OUT, f), "www-data", "www-data")
    shutil.chown(OUT, "www-data", "www-data")
except Exception:
    pass
print("\nAPPLIED - %d pages, %d footer links, %d sitemap urls. Backups in %s" % (len(built), len(foot), add.count("<url>"), bak))
