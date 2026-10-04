"""Import terminals (and websites, helplines) from the official Daewoo and Niazi Express websites. Public pages only.
Timings are not imported: they are only inside the companies' booking search (protected by reCAPTCHA)."""
import html
import re
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from bus.models import Company, Terminal

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
MULTI = ["dera ismail khan", "dera ghazi khan", "rahim yar khan", "mandi bahauddin", "toba tek singh", "chak jhumra", "kot addu", "ahmed pur east", "haweli lakha", "peer mahal"]


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")


def lines(page):
    body = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", page)
    out = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x))).strip() for x in re.split(r"(?i)<br\s*/?>|</(?:p|div|li|h\d|td|tr|span)>", body)]
    return [x for x in out if 2 < len(x) < 200]


def city_of(name):
    n = re.sub(r"\(.*?\)", "", name).strip().lower().replace("-", " ")
    for m in MULTI:
        if n.startswith(m): return m.title()
    return (n.split() or [""])[0].title()


def maps(q):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)


def helpline(page):
    m = re.search(r"(?:UAN|Helpline|Call)[^0-9+]{0,25}((?:\+92[- ]?)?0?\d{2,4}[- ]?\d{3}[- ]?\d{3,4})", re.sub(r"<[^>]+>", " ", page), re.I)
    return m.group(1).strip() if m else ""


def parse_daewoo(L):
    out = []
    for i, x in enumerate(L):
        if x.lower().startswith("address:") and i > 0:
            name = L[i - 1]; addr = re.sub(r"(?i)^address:\s*", "", x).strip().rstrip(",")
            phone = re.sub(r"(?i)^phone:\s*", "", L[i + 1]).strip() if i + 1 < len(L) and L[i + 1].lower().startswith("phone:") else ""
            if name.isupper() or name.istitle():
                out.append((city_of(name), name.title(), addr, phone))
    return out


def parse_niazi(L):
    try:
        start = next(i for i, x in enumerate(L) if "OUR TERMINALS" in x.upper() and len(x) > 14)
    except StopIteration:
        return []
    out = []
    for x in L[start + 1:]:
        if re.match(r"^[A-Z][A-Za-z\- ]{2,30}$", x) and len(x.split()) <= 3 and not re.search(r"ride|comfort|read more|niazi|service", x, re.I):
            out.append(x.replace("-", " ").title())
        elif out and re.search(r"ride with|copyright|contact", x, re.I):
            break
    return out


class Command(BaseCommand):
    help = "Import Daewoo and Niazi Express terminals from their official websites."

    def handle(self, *a, **o):
        n = 0
        try:
            home = fetch("https://daewoo.com.pk")
            d, _ = Company.objects.update_or_create(name="Daewoo Express", defaults={"website": "https://daewoo.com.pk"})
            h = helpline(home)
            if h and not d.helpline: d.helpline = h[:40]; d.save()
            for city, name, addr, phone in parse_daewoo(lines(fetch("https://daewoo.com.pk/Home/Terminals"))):
                label = (name + ": " + addr + (" \u00b7 \u260E " + phone if phone else ""))[:120]
                Terminal.objects.update_or_create(company=d, city=city, name=label, defaults={"map_url": maps("Daewoo Express " + name + " " + addr)[:400]}); n += 1
            self.stdout.write("Daewoo: %d terminals%s" % (n, (", helpline " + d.helpline) if d.helpline else ""))
        except Exception as e:
            self.stderr.write("Daewoo: %s" % e)
        m = 0
        try:
            home = fetch("https://www.niaziexpress.com.pk")
            z, _ = Company.objects.update_or_create(name="Niazi Express", defaults={"website": "https://www.niaziexpress.com.pk/online-booking/"})
            h = helpline(home)
            if h and not z.helpline: z.helpline = h[:40]; z.save()
            for city in parse_niazi(lines(fetch("https://www.niaziexpress.com.pk/our-terminals/"))):
                Terminal.objects.update_or_create(company=z, city=city, name="Niazi Express " + city + " terminal", defaults={"map_url": maps("Niazi Express terminal " + city)}); m += 1
            self.stdout.write("Niazi: %d terminals%s" % (m, (", helpline " + z.helpline) if z.helpline else ""))
        except Exception as e:
            self.stderr.write("Niazi: %s" % e)
