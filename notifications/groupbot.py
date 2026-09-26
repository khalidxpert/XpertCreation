"""The group bot - an eggdrop for XpertCreation groups.

It greets new members by name, keeps order (bad words, flood, links), knows the group's moderators,
answers !commands (date, time, weather, prayer times, DNS, calculator, games...) and posts timed messages.
Everything it does is written to the bot log that admins can read."""
import ast
import operator
import random
import re
from datetime import datetime, timedelta

import requests
from django.core.cache import cache
from django.utils import timezone

from .models import ChatGroup, GroupBan, GroupBot, GroupBotLog, GroupBotTimer, GroupMember, GroupMessage

PK_TZ = "Asia/Karachi"
LINK = re.compile(r"(https?://|www\.)\S+|\b[a-z0-9-]+\.(com|pk|net|org|io|me|info|xyz|link|ly)\b", re.I)


def bot_for(g):
    b, _ = GroupBot.objects.get_or_create(group=g)
    return b


def _name(u):
    return ((getattr(u, "full_name", "") or "").strip() or "Member") if u else "someone"


def say(g, text, bot=None):
    bot = bot or bot_for(g)
    m = GroupMessage.objects.create(group=g, body=str(text)[:2000], system=False, bot=True)
    ChatGroup.objects.filter(pk=g.pk).update(updated_at=timezone.now())
    return m


def log(g, action, target="", by="", reason=""):
    GroupBotLog.objects.create(group=g, action=action, target=str(target)[:120], by=str(by)[:120], reason=str(reason)[:200])


def is_mod(member):
    return bool(member and (member.role == "admin" or member.bot_mod))


def greet(g, user):
    b = bot_for(g)
    if b.enabled and b.greeting:
        say(g, b.greeting.replace("{name}", _name(user).split(" ")[0]).replace("{group}", g.name), b)


def intro(g):
    b = bot_for(g)
    say(g, "\U0001F916 Hi, I am %s, this group's bot. I welcome new members, keep things tidy and answer commands. Type !help to see them." % b.name, b)


# ---------------------------------------------------------------- moderation on every message

def _words(b):
    return [w.strip().lower() for w in re.split(r"[,\n]", b.bad_words or "") if w.strip()]


def mute(g, member, minutes, by, reason):
    member.muted_until = timezone.now() + timedelta(minutes=minutes)
    member.warnings = 0
    member.save(update_fields=["muted_until", "warnings"])
    log(g, "mute", _name(member.user), by, "%s (%d min)" % (reason, minutes))


def check(g, member, text):
    """Called before a message is saved. Returns an error for the sender, or None if it may go out."""
    b = bot_for(g)
    now = timezone.now()
    if member.muted_until and member.muted_until > now:
        left = int((member.muted_until - now).total_seconds() // 60) + 1
        return "You are muted in this group for %d more minute%s." % (left, "" if left == 1 else "s")
    if not b.enabled or is_mod(member):
        return None
    low = (text or "").lower()
    hit = next((w for w in _words(b) if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low)), None)
    link = b.links_admins_only and LINK.search(text or "")
    if hit or link:
        member.warnings += 1
        member.save(update_fields=["warnings"])
        why = "a word this group does not allow" if hit else "a link (only admins and moderators can post links here)"
        log(g, "blocked", _name(member.user), b.name, why)
        if member.warnings >= b.warn_limit:
            mute(g, member, b.mute_minutes, b.name, "too many warnings")
            say(g, "\U0001F507 %s has been muted for %d minutes after %d warnings." % (_name(member.user).split(" ")[0], b.mute_minutes, b.warn_limit), b)
            return "Your message was not sent and you are now muted for %d minutes." % b.mute_minutes
        return "Your message was not sent: it contains %s. Warning %d of %d." % (why, member.warnings, b.warn_limit)
    recent = GroupMessage.objects.filter(group=g, author=member.user, created_at__gte=now - timedelta(seconds=b.flood_seconds)).count()
    if recent >= b.flood_count:
        mute(g, member, 5, b.name, "flooding")
        say(g, "\U0001F507 %s is sending too fast and is muted for 5 minutes." % _name(member.user).split(" ")[0], b)
        return "Slow down - you are muted for 5 minutes."
    return None


# ---------------------------------------------------------------- friendly helpers

def _get(url, params=None, headers=None, key=None, ttl=600):
    if key:
        hit = cache.get(key)
        if hit is not None:
            return hit
    try:
        r = requests.get(url, params=params, headers=headers or {"User-Agent": "XpertCreation-bot"}, timeout=6)
        d = r.json() if r.ok else None
    except Exception:
        d = None
    if key and d is not None:
        cache.set(key, d, ttl)
    return d


def _place(q):
    q = (q or "").strip()[:60]
    if not q:
        return None
    d = _get("https://geocoding-api.open-meteo.com/v1/search", {"name": q, "count": 1, "language": "en"}, key="geo:" + q.lower(), ttl=86400)
    r = (d or {}).get("results") or []
    return r[0] if r else None


WEATHER = {0: "clear sky \u2600\uFE0F", 1: "mostly clear \U0001F324", 2: "partly cloudy \u26C5", 3: "cloudy \u2601\uFE0F", 45: "fog \U0001F32B", 48: "fog \U0001F32B",
           51: "light drizzle \U0001F326", 53: "drizzle \U0001F326", 55: "heavy drizzle \U0001F327", 61: "light rain \U0001F326", 63: "rain \U0001F327", 65: "heavy rain \U0001F327",
           71: "light snow \U0001F328", 73: "snow \U0001F328", 75: "heavy snow \u2744\uFE0F", 80: "rain showers \U0001F326", 81: "rain showers \U0001F327", 82: "violent showers \u26C8",
           95: "thunderstorm \u26C8", 96: "thunderstorm with hail \u26C8", 99: "thunderstorm with hail \u26C8"}

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
       ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


def _calc(expr):
    expr = expr.replace("x", "*").replace("\u00d7", "*").replace("\u00f7", "/").replace("^", "**").replace(",", "")
    if len(expr) > 80:
        raise ValueError

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and (abs(b) > 100 or abs(a) > 1e6):
                raise ValueError
            return OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
            return OPS[type(n.op)](ev(n.operand))
        raise ValueError
    v = ev(ast.parse(expr, mode="eval"))
    return int(v) if float(v).is_integer() and abs(v) < 1e15 else round(v, 6)


JOKES = ["Why did the computer go to the doctor? It had a virus! \U0001F912", "Teacher: Why are you late? Student: Because of the sign - 'School ahead, go slow' \U0001F605",
         "I told my phone a joke. It didn't laugh - it just auto-corrected me. \U0001F4F1", "Why do programmers prefer dark mode? Because light attracts bugs. \U0001F41B",
         "My WiFi and I have a lot in common: we both lose connection when things get serious. \U0001F4F6", "Why was the math book sad? It had too many problems. \U0001F4DA",
         "Chai without biscuits is like WiFi without password - incomplete. \u2615", "I asked the elevator how it was doing. It said: 'Up and down.' \U0001F6D7",
         "Why did the scarecrow win an award? He was outstanding in his field. \U0001F33E", "Parking in Lahore is easy - if you have a helicopter. \U0001F681"]
QUOTES = ["\u201cThe best of people are those that bring most benefit to others.\u201d", "\u201cSmall steps every day add up to big results.\u201d",
          "\u201cKnowledge is the life of the mind.\u201d \u2014 Hazrat Ali (RA)", "\u201cDreams are not what you see in sleep; they are the things that do not let you sleep.\u201d \u2014 A.P.J. Abdul Kalam",
          "\u201cWork while they sleep. Learn while they party.\u201d", "\u201cWith hardship comes ease.\u201d \u2014 Quran 94:6",
          "\u201cDo not wait for the perfect moment; take the moment and make it perfect.\u201d", "\u201cA kind word is a form of charity.\u201d",
          "\u201cDiscipline is choosing between what you want now and what you want most.\u201d", "\u201cThe expert in anything was once a beginner.\u201d"]
BALL = ["Yes \u2705", "No \u274C", "Maybe \U0001F914", "Definitely! \U0001F4AF", "Ask again later \u23F3", "I don't think so \U0001F645", "InshaAllah \U0001F932", "Very likely \U0001F44D", "Not now \u270B"]


def _find(g, who):
    """'@Saleem' or 'Saleem Iqbal' -> the member, by start of full or first name."""
    who = (who or "").strip().lstrip("@").lower()
    if not who:
        return None, "Say who, for example: @Saleem"
    ms = [m for m in GroupMember.objects.filter(group=g).select_related("user") if _name(m.user).lower().startswith(who)
          or _name(m.user).lower().split(" ")[0] == who]
    if not ms:
        return None, "I can't find anyone called %s in this group." % who
    if len(ms) > 1:
        return None, "More than one member matches %s: %s. Use more of the name." % (who, ", ".join(_name(m.user) for m in ms[:5]))
    return ms[0], None


def _split_target(args):
    """'@Saleem Iqbal 30m spamming' -> ('Saleem Iqbal', '30m spamming') using the members' real names."""
    return args


def _duration(s, default):
    m = re.match(r"^(\d{1,4})\s*([mhd]?)$", (s or "").strip().lower())
    if not m:
        return default
    n, u = int(m.group(1)), m.group(2) or "m"
    return min(n * {"m": 1, "h": 60, "d": 1440}[u], 30 * 1440)


HELP_ALL = ("\U0001F916 Commands for everyone:\n!help  !rules  !admins  !ping\n!date  !hijri  !time [city]\n!weather <city>  !prayer [city]\n!dns <domain> [A|MX|TXT|NS]\n"
            "!calc <sum>  !roll [2d6]  !coin  !8ball <question>\n!joke  !quote  !seen @name  !whois @name  !stats")
HELP_MOD = ("\n\n\U0001F6E1 For moderators and admins:\n!warn @name [reason]\n!mute @name [30m|2h|1d]  !unmute @name\n!kick @name  !ban @name  !unban name  !bans\n"
            "!pin (pins the message before)  !unpin\n!clear [10]  !topic <text>\n!lock  !unlock (only admins can send)")


def _target_and_rest(g, args):
    """Try the longest name first so '@Saleem Iqbal 2h' works with a two-word name."""
    parts = (args or "").lstrip("@").split()
    for n in range(min(4, len(parts)), 0, -1):
        m, err = _find(g, " ".join(parts[:n]))
        if m:
            return m, " ".join(parts[n:]), None
    return None, "", (_find(g, parts[0] if parts else "")[1])


def command(g, member, text):
    """Handle a !command after the member's message has been saved. The bot answers in the group."""
    b = bot_for(g)
    if not b.enabled:
        return
    parts = text.strip().split(None, 1)
    cmd, args = parts[0][1:].lower(), (parts[1] if len(parts) > 1 else "").strip()
    me = _name(member.user)
    first = me.split(" ")[0]
    if not cache.add("botcmd:%d:%d" % (g.id, member.user_id), 1, 2):
        return
    reply = None
    now = timezone.localtime(timezone.now())
    mod = is_mod(member)
    if cmd == "help":
        reply = HELP_ALL + (HELP_MOD if mod else "")
    elif cmd == "rules":
        reply = "\U0001F4DC Rules of %s:\n%s" % (g.name, b.rules or "No rules set yet.")
    elif cmd == "ping":
        reply = "Pong! \U0001F3D3"
    elif cmd == "admins":
        ms = GroupMember.objects.filter(group=g).select_related("user")
        a = [_name(m.user) for m in ms if m.role == "admin"]
        mm = [_name(m.user) for m in ms if m.role != "admin" and m.bot_mod]
        reply = "\U0001F451 Admins: %s%s" % (", ".join(a) or "none", ("\n\U0001F6E1 Moderators: " + ", ".join(mm)) if mm else "")
    elif cmd == "date":
        reply = "\U0001F4C5 %s" % now.strftime("%A, %d %B %Y")
        h = _get("https://api.aladhan.com/v1/gToH/%s" % now.strftime("%d-%m-%Y"), key="hijri:" + now.strftime("%Y%m%d"), ttl=21600)
        try:
            hd = h["data"]["hijri"]
            reply += "\n\U0001F319 %s %s %s AH" % (hd["day"], hd["month"]["en"], hd["year"])
        except Exception:
            pass
    elif cmd == "hijri":
        h = _get("https://api.aladhan.com/v1/gToH/%s" % now.strftime("%d-%m-%Y"), key="hijri:" + now.strftime("%Y%m%d"), ttl=21600)
        try:
            hd = h["data"]["hijri"]
            reply = "\U0001F319 %s %s %s AH (%s)" % (hd["day"], hd["month"]["en"], hd["year"], hd["month"]["ar"])
        except Exception:
            reply = "I can't reach the Hijri calendar right now. Try again later."
    elif cmd == "time":
        if not args:
            reply = "\U0001F552 Pakistan time: %s" % now.strftime("%I:%M %p, %a %d %b")
        else:
            p = _place(args)
            if not p or not p.get("timezone"):
                reply = "I don't know a place called %s." % args[:40]
            else:
                from zoneinfo import ZoneInfo
                t = datetime.now(ZoneInfo(p["timezone"]))
                reply = "\U0001F552 %s, %s: %s" % (p["name"], p.get("country", ""), t.strftime("%I:%M %p, %a %d %b"))
    elif cmd == "weather":
        p = _place(args or "Lahore")
        if not p:
            reply = "I don't know a place called %s." % args[:40]
        else:
            d = _get("https://api.open-meteo.com/v1/forecast", {"latitude": p["latitude"], "longitude": p["longitude"],
                     "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m", "timezone": "auto"},
                     key="wx:%.2f:%.2f" % (p["latitude"], p["longitude"]), ttl=900)
            c = (d or {}).get("current")
            reply = ("\U0001F326 %s, %s: %.0f\u00b0C, %s, humidity %d%%, wind %.0f km/h" % (p["name"], p.get("country", ""), c["temperature_2m"],
                     WEATHER.get(c["weather_code"], "\u2014"), c["relative_humidity_2m"], c["wind_speed_10m"])) if c else "I can't get the weather right now."
    elif cmd in ("prayer", "namaz", "salah"):
        p = _place(args or "Lahore")
        if not p:
            reply = "I don't know a place called %s." % args[:40]
        else:
            d = _get("https://api.aladhan.com/v1/timings/%s" % now.strftime("%d-%m-%Y"), {"latitude": p["latitude"], "longitude": p["longitude"], "method": 1, "school": 1},
                     key="pray:%s:%.2f:%.2f" % (now.date(), p["latitude"], p["longitude"]), ttl=21600)
            try:
                t = d["data"]["timings"]
                reply = "\U0001F54C Prayer times, %s (Hanafi): Fajr %s \u00b7 Sunrise %s \u00b7 Dhuhr %s \u00b7 Asr %s \u00b7 Maghrib %s \u00b7 Isha %s" % (
                    p["name"], t["Fajr"], t["Sunrise"], t["Dhuhr"], t["Asr"], t["Maghrib"], t["Isha"])
            except Exception:
                reply = "I can't get prayer times right now."
    elif cmd == "dns":
        a = args.split()
        dom = (a[0] if a else "").lower().strip().rstrip(".")
        typ = (a[1].upper() if len(a) > 1 else "A")
        if not re.match(r"^(?=.{3,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,24}$", dom) or typ not in ("A", "AAAA", "MX", "TXT", "NS", "CNAME"):
            reply = "Use it like: !dns xpertcreation.com  or  !dns gmail.com MX"
        else:
            d = _get("https://cloudflare-dns.com/dns-query", {"name": dom, "type": typ}, headers={"accept": "application/dns-json"}, key="dns:%s:%s" % (dom, typ), ttl=300)
            ans = [x.get("data", "") for x in (d or {}).get("Answer", []) if x.get("data")]
            reply = ("\U0001F310 %s %s:\n%s" % (dom, typ, "\n".join(ans[:8]))) if ans else "\U0001F310 No %s record for %s." % (typ, dom)
    elif cmd == "calc":
        try:
            reply = "\U0001F9EE %s = %s" % (args, _calc(args))
        except Exception:
            reply = "I can only do sums like: !calc (25+15)*3/2"
    elif cmd == "roll":
        m = re.match(r"^(\d{0,2})d(\d{1,3})$", args.lower()) or re.match(r"^()(\d{1,3})$", args)
        n, s = (int(m.group(1) or 1), int(m.group(2))) if m else (1, 6)
        n, s = max(1, min(n, 10)), max(2, min(s, 1000))
        rolls = [random.randint(1, s) for _ in range(n)]
        reply = "\U0001F3B2 %s rolled %s%s" % (first, ", ".join(map(str, rolls)), (" = %d" % sum(rolls)) if n > 1 else "")
    elif cmd == "coin":
        reply = "\U0001FA99 %s tossed a coin: %s" % (first, random.choice(["Heads", "Tails"]))
    elif cmd == "8ball":
        reply = "\U0001F3B1 %s" % random.choice(BALL) if args else "Ask me a question, like: !8ball Will it rain today?"
    elif cmd == "joke":
        reply = random.choice(JOKES)
    elif cmd == "quote":
        reply = "\U0001F4AC " + random.choice(QUOTES)
    elif cmd in ("seen", "whois"):
        t, err = _find(g, args)
        if not t:
            reply = err
        elif cmd == "seen":
            reply = ("\U0001F440 %s last wrote here %s." % (_name(t.user), timezone.localtime(t.last_seen).strftime("%d %b at %I:%M %p"))) if t.last_seen else "\U0001F440 %s hasn't written here yet." % _name(t.user)
        else:
            role = "Admin" if t.role == "admin" else ("Moderator" if t.bot_mod else "Member")
            reply = "\U0001F464 %s \u00b7 %s \u00b7 joined %s \u00b7 %d messages%s" % (_name(t.user), role, timezone.localtime(t.joined_at).strftime("%d %b %Y"),
                                                                                  t.msg_count, (" \u00b7 %d warning(s)" % t.warnings) if mod and t.warnings else "")
    elif cmd == "stats":
        ms = GroupMember.objects.filter(group=g).select_related("user").order_by("-msg_count")
        top = [("%s (%d)" % (_name(m.user).split(" ")[0], m.msg_count)) for m in ms[:5] if m.msg_count]
        reply = "\U0001F4CA %s: %d members, %d messages, since %s.%s" % (g.name, ms.count(), GroupMessage.objects.filter(group=g, bot=False, system=False).count(),
                                                                       timezone.localtime(g.created_at).strftime("%d %b %Y"), ("\nMost active: " + ", ".join(top)) if top else "")
    elif cmd in ("warn", "mute", "unmute", "kick", "ban", "unban", "bans", "pin", "unpin", "clear", "topic", "lock", "unlock"):
        if not mod:
            reply = "\u26D4 %s, only moderators and admins can use !%s." % (first, cmd)
        else:
            reply = _mod_command(g, b, member, cmd, args)
    if reply:
        say(g, reply, b)


def _can_act(actor, target):
    if target.user_id == actor.user_id:
        return "You can't do that to yourself."
    if target.role == "admin":
        return "Admins can't be moderated by the bot."
    if target.bot_mod and actor.role != "admin":
        return "Only admins can act on another moderator."
    return None


def _mod_command(g, b, actor, cmd, args):
    who = _name(actor.user)
    if cmd == "bans":
        bans = GroupBan.objects.filter(group=g).select_related("user")[:20]
        return "\u26D4 Banned: " + (", ".join(_name(x.user) for x in bans) if bans else "nobody")
    if cmd == "unban":
        name = args.lstrip("@").strip().lower()
        ban = next((x for x in GroupBan.objects.filter(group=g).select_related("user") if name and _name(x.user).lower().startswith(name)), None)
        if not ban:
            return "No banned member matches %s." % (args or "that name")
        ban.delete(); log(g, "unban", _name(ban.user), who)
        return "\u2705 %s is no longer banned and can join again." % _name(ban.user)
    if cmd in ("pin", "unpin"):
        if cmd == "unpin":
            n = GroupMessage.objects.filter(group=g, pinned=True).update(pinned=False)
            return "\U0001F4CC Unpinned %d message%s." % (n, "" if n == 1 else "s")
        prev = GroupMessage.objects.filter(group=g, bot=False, system=False, hidden=False).exclude(body__startswith="!").order_by("-id").first()
        if not prev:
            return "There is no message to pin."
        pin(g, prev)
        return "\U0001F4CC Pinned the message from %s." % (_name(prev.author) if prev.author_id else "the group")
    if cmd == "clear":
        try:
            n = max(1, min(int(args or 10), 50))
        except ValueError:
            n = 10
        ids = list(GroupMessage.objects.filter(group=g, hidden=False).exclude(bot=True).order_by("-id").values_list("id", flat=True)[:n + 1])[1:]
        GroupMessage.objects.filter(id__in=ids).update(hidden=True, pinned=False)
        log(g, "clear", "%d messages" % len(ids), who)
        return "\U0001F9F9 %s cleared the last %d message%s." % (who.split(" ")[0], len(ids), "" if len(ids) == 1 else "s")
    if cmd == "topic":
        if not args:
            return "Use it like: !topic Welcome! Today we talk about Excel."
        g.description = args[:300]; g.save(update_fields=["description", "updated_at"]); log(g, "topic", "", who, args)
        return "\U0001F4DD New topic: %s" % args[:300]
    if cmd in ("lock", "unlock"):
        g.only_admins_send = cmd == "lock"; g.save(update_fields=["only_admins_send", "updated_at"]); log(g, cmd, "", who)
        return "\U0001F512 The group is locked: only admins can send messages." if cmd == "lock" else "\U0001F513 The group is open: everyone can send messages again."
    t, rest, err = _target_and_rest(g, args)
    if not t:
        return err
    bad = _can_act(actor, t)
    if bad:
        return bad
    tn = _name(t.user)
    if cmd == "warn":
        t.warnings += 1; t.save(update_fields=["warnings"]); log(g, "warn", tn, who, rest)
        if t.warnings >= b.warn_limit:
            mute(g, t, b.mute_minutes, who, "too many warnings")
            return "\U0001F507 %s reached %d warnings and is muted for %d minutes." % (tn, b.warn_limit, b.mute_minutes)
        return "\u26A0\uFE0F %s, this is a warning (%d of %d)%s." % (tn, t.warnings, b.warn_limit, (": " + rest) if rest else "")
    if cmd == "mute":
        bits = rest.split(None, 1)
        mins = _duration(bits[0] if bits else "", b.mute_minutes)
        reason = bits[1] if len(bits) > 1 and _duration(bits[0], -1) != -1 else rest
        mute(g, t, mins, who, reason or "muted by a moderator")
        return "\U0001F507 %s is muted for %s%s." % (tn, ("%d min" % mins) if mins < 60 else ("%d h" % (mins // 60) if mins < 1440 else "%d day(s)" % (mins // 1440)), (": " + reason) if reason else "")
    if cmd == "unmute":
        t.muted_until = None; t.save(update_fields=["muted_until"]); log(g, "unmute", tn, who)
        return "\U0001F50A %s can send messages again." % tn
    if cmd in ("kick", "ban"):
        if cmd == "ban":
            GroupBan.objects.get_or_create(group=g, user=t.user, defaults={"by": actor.user, "reason": rest[:200]})
        t.delete(); log(g, cmd, tn, who, rest)
        return ("\U0001F462 %s was removed from the group%s." if cmd == "kick" else "\u26D4 %s is banned from this group%s.") % (tn, (": " + rest) if rest else "")
    return None


def pin(g, m):
    """Pin a message; keep at most 3 pinned (the oldest pin drops off)."""
    m.pinned, m.pinned_at = True, timezone.now()
    m.save(update_fields=["pinned", "pinned_at"])
    for old in GroupMessage.objects.filter(group=g, pinned=True).order_by("-pinned_at")[3:]:
        GroupMessage.objects.filter(pk=old.pk).update(pinned=False)


def banned(g, user):
    return GroupBan.objects.filter(group=g, user=user).exists()


def next_run(t, after=None):
    after = after or timezone.now()
    if t.daily_at:
        local = timezone.localtime(after)
        run = local.replace(hour=t.daily_at.hour, minute=t.daily_at.minute, second=0, microsecond=0)
        if run <= local:
            run += timedelta(days=1)
        return run
    return after + timedelta(hours=max(1, t.every_hours or 24))


def run_timers():
    n = 0
    for t in GroupBotTimer.objects.filter(next_run__lte=timezone.now()).select_related("group")[:200]:
        b = bot_for(t.group)
        if b.enabled:
            say(t.group, t.text, b); n += 1
        t.next_run = next_run(t)
        t.save(update_fields=["next_run"])
    return n
