#!/usr/bin/env python3
# Makes one static SEO page per tool from tools.html.
#   python3 gen_tool_pages.py            dry run -> /tmp/toolpages
#   python3 gen_tool_pages.py --apply    live   -> tools-pages/ + sitemap
# Re-run with --apply after ANY change to tools.html.
import re, sys, os, json, html, shutil
from datetime import datetime

SRC     = "/var/www/xpertcreation-landing/tools.html"
LIVE    = "/var/www/xpertcreation-landing/tools-pages"
DRY     = "/tmp/toolpages"
SITEMAP = "/var/www/xpertcreation-landing/sitemap.xml"
BASE    = "https://xpertcreation.com/tools/"
APPLY   = "--apply" in sys.argv
OUT     = LIVE if APPLY else DRY
STAMP   = datetime.now().strftime("%Y%m%d_%H%M%S")

# These already have their own pages elsewhere on the site.
SKIP = {"card", "vcard", "typingtutor", "wx", "vibecheck", "bizapp"}

GROUPS = {"maths": "maths", "time": "date and time", "health": "health",
          "money": "money", "convert": "converter", "text": "text",
          "daily": "everyday", "dev": "developer", "web": "domain and web"}

# id: (slug, title, description) - the ones people search for most.
SEO = {
 "fbrtax":   ("income-tax-calculator-pakistan", "Income Tax Calculator Pakistan - FBR Salary Tax",
              "Work out income tax on your salary in Pakistan using the current FBR slabs. Enter your salary and see the tax straight away."),
 "bijli":    ("electricity-bill-calculator", "Electricity Bill Calculator Pakistan - Units to Rupees",
              "Turn electricity units into rupees using the slab rates. Check your bill before it arrives and see how the slabs add up."),
 "age":      ("age-calculator", "Age Calculator - Exact Age in Years, Months and Days",
              "Find your exact age in years, months and days, and how many days are left until your next birthday."),
 "area":     ("marla-kanal-calculator", "Marla and Kanal to Square Feet Converter",
              "Convert marla, kanal, square feet, acres and hectares. Handy for plots and property in Pakistan."),
 "zakat":    ("zakat-calculator", "Zakat Calculator - 2.5% of Zakatable Wealth",
              "Work out how much zakat is due on your zakatable wealth at 2.5%."),
 "aggregate":("aggregate-calculator", "Aggregate Calculator - Admission Merit for MDCAT, ECAT and University",
              "Work out your admission aggregate with your own weightings for matric, intermediate and entry test marks."),
 "gpa":      ("gpa-cgpa-calculator", "GPA and CGPA Calculator",
              "Work out your GPA or CGPA from school marks or university credit hours."),
 "percent":  ("percentage-calculator", "Percentage Calculator",
              "Answer five kinds of percentage question: percent of a number, increase, decrease, and more."),
 "qr":       ("qr-code-generator", "Free QR Code Generator",
              "Make a QR code for a link, a phone number or any text. Free, no sign-up."),
 "walink":   ("whatsapp-link-generator", "WhatsApp Link Generator - Message Without Saving the Number",
              "Open a WhatsApp chat with any number without saving it to your contacts first."),
 "passport": ("passport-photo-maker", "Passport Photo Maker - Crop to Passport Size",
              "Crop your photo to passport size on your phone, ready to print."),
 "prayer":   ("prayer-times", "Prayer Times Today - Namaz Timings for Your City",
              "Today's namaz timings for where you are: Fajr, Zuhr, Asr, Maghrib and Isha."),
 "numwords": ("number-to-words", "Number to Words Converter - for Cheques and Forms",
              "Write any amount in words, the way cheques and forms need it."),
 "loan":     ("loan-emi-calculator", "Loan EMI Calculator - Monthly Payment and Total Interest",
              "Work out the monthly payment on a loan and how much interest you pay in total."),
 "bmi":      ("bmi-calculator", "BMI Calculator - With the Healthy Range for Your Height",
              "Work out your body mass index and see the healthy weight range for your height."),
 "words":    ("word-counter", "Word Counter - Words, Characters and Reading Time",
              "Count words and characters in any text, and see how long it takes to read."),
 "pass":     ("password-generator", "Strong Password Generator",
              "Make strong random passwords on your own device. Nothing is sent anywhere."),
 "duedate":  ("pregnancy-due-date-calculator", "Pregnancy Due Date Calculator",
              "Work out your due date and pregnancy dates from the first day of your last period."),
 "weight":   ("weight-converter", "Weight Converter - kg, Pound, Tola, Maund and Seer",
              "Convert between kg, grams, pounds, ounces, tola, maund and seer."),
 "calc":     ("scientific-calculator", "Online Scientific Calculator",
              "A scientific calculator with powers, roots, trigonometry, logs and factorials."),
 "gst":      ("sales-tax-calculator", "GST and Sales Tax Calculator",
              "Add sales tax to a price, or work out the tax inside a total."),
 "qibla":    ("qibla-direction", "Qibla Direction Finder - Which Way to Pray From Your Location",
              "Find the Qibla direction from where you are, in degrees from North, with the distance to the Kaaba."),
 "hijri":    ("hijri-date-converter", "Hijri Date Converter - Islamic Date Today and Back to English",
              "Convert an English date to the Hijri (Islamic) date and back, using the Umm al-Qura calendar."),
 "tasbeeh":  ("tasbeeh-counter", "Online Tasbeeh Counter - Digital Tasbih for Dhikr",
              "A digital tasbeeh counter with a target of 33, 99 or 100. The count stays on your phone."),
 "dns":      ("dns-lookup", "DNS Lookup - A, MX, TXT, NS, CNAME and CAA Records",
              "Look up the DNS records of any domain: A, AAAA, MX, TXT, NS, CNAME and CAA. Free and instant."),
 "rdap":     ("domain-whois-lookup", "Domain WHOIS Lookup - Registrar, Expiry Date and Age",
              "See when a domain was registered, when it expires, its registrar, age and nameservers."),
 "myip":     ("what-is-my-ip", "What Is My IP Address",
              "See your public IP address, IPv4 or IPv6, and the country websites see you in."),
 "mailcheck":("email-spf-dmarc-check", "Email Setup Check - MX, SPF and DMARC",
              "Check whether a domain's email is set up properly: mail servers, SPF and DMARC, with plain advice."),
 "clock":    ("world-clock", "World Clock - Time in Other Countries",
              "See the time in other countries side by side."),
}

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def js_str(s):
    return json.loads('"%s"' % s)          # turns \u2014 into a real dash

src = open(SRC, encoding="utf-8").read()

tools = []
for m in re.finditer(r'\{\s*id:"([^"]+)",\s*g:"([^"]+)".*?name:"([^"]+)",\s*blurb:"([^"]*)"', src, re.S):
    tid, g, name, blurb = m.group(1), m.group(2), js_str(m.group(3)), js_str(m.group(4))
    if tid in SKIP:
        continue
    if tid in SEO:
        slug, title, desc = SEO[tid]
    else:
        slug  = slugify(name)
        title = "%s - %s" % (name, blurb)
        desc  = "%s. Free online tool, no sign-up." % blurb.rstrip(".")
    tools.append(dict(id=tid, g=g, name=name, blurb=blurb, slug=slug, title=title, desc=desc))

print("tools found:", len(tools), "(skipped %d)" % len(SKIP))
slugs = [t["slug"] for t in tools]
dupes = sorted(set(s for s in slugs if slugs.count(s) > 1))
if dupes:
    sys.exit("STOP - duplicate slugs: %s" % dupes)

# Anchors must each be found exactly once in tools.html.
A_TITLE = re.compile(r"<title>.*?</title>", re.S)
A_DESC  = re.compile(r'<meta name="description" content="[^"]*">')
A_CANON = '<link rel="canonical" href="https://xpertcreation.com/tools">'
A_WANT  = '  var want = new URLSearchParams(location.search).get("t");'
A_APP   = '<div class="wrap"><div id="app"></div></div>'
problems = []
for label, n in (("title", len(A_TITLE.findall(src))), ("description", len(A_DESC.findall(src))),
                 ("canonical", src.count(A_CANON)), ("want line", src.count(A_WANT)),
                 ("app div", src.count(A_APP))):
    print("  anchor %-12s %d" % (label, n))
    if n != 1:
        problems.append(label)
if problems:
    sys.exit("STOP - anchors not found once: %s" % problems)

STYLE = ('<style>.seo{margin-top:32px;line-height:1.65;opacity:.92}.seo h2{font-size:1.15em;margin:0 0 8px}'
         '.seo h3{font-size:1em;margin:18px 0 6px}.seo ul{padding-left:18px;margin:0}.seo li{margin:3px 0}</style>')

def page_for(t):
    e = html.escape
    url = BASE + t["slug"]
    same = [x for x in tools if x["g"] == t["g"] and x["id"] != t["id"]][:8]
    links = "".join('<li><a href="/tools/%s">%s</a> - %s</li>' % (x["slug"], e(x["name"]), e(x["blurb"])) for x in same)
    seo = ('\n<section class="wrap seo">'
           '<h2>%s</h2><p>%s</p>'
           '<p>Free to use, with no sign-up, and it works just as well on a phone as on a computer.</p>'
           % (e(t["title"]), e(t["desc"])))
    if links:
        seo += '<h3>More %s tools</h3><ul>%s</ul>' % (GROUPS.get(t["g"], t["g"]), links)
    seo += '<p><a href="/tools">See all %d tools</a></p></section>\n' % len(tools)

    p = src
    p = A_TITLE.sub(lambda m: "<title>%s | XpertCreation</title>" % e(t["title"]), p, 1)
    p = A_DESC.sub(lambda m: '<meta name="description" content="%s">' % e(t["desc"]), p, 1)
    p = p.replace(A_CANON, '<link rel="canonical" href="%s">' % url, 1)
    p = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: m.group(1) + e(t["title"]) + m.group(2), p)
    p = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + e(t["desc"]) + m.group(2), p)
    p = re.sub(r'(<meta property="og:url" content=")[^"]*(")', lambda m: m.group(1) + url + m.group(2), p)
    p = p.replace(A_WANT, '  var want = new URLSearchParams(location.search).get("t") || "%s";' % t["id"], 1)
    p = p.replace(A_APP, A_APP + seo + STYLE, 1)
    return p

if APPLY and os.path.isdir(OUT):
    shutil.move(OUT, "/root/toolpages_bak_" + STAMP)
    print("old pages moved to /root/toolpages_bak_" + STAMP)
os.makedirs(OUT, exist_ok=True)
for t in tools:
    open(os.path.join(OUT, t["slug"] + ".html"), "w", encoding="utf-8").write(page_for(t))
print("written:", len(tools), "pages to", OUT)

if APPLY:
    sm = open(SITEMAP, encoding="utf-8").read()
    shutil.copy(SITEMAP, "/root/sitemap.xml.bak_" + STAMP)
    add = "".join("  <url><loc>%s%s</loc></url>\n" % (BASE, t["slug"])
                  for t in tools if (BASE + t["slug"] + "<") not in sm)
    if "</urlset>" not in sm:
        sys.exit("STOP - no </urlset> in sitemap")
    sm = sm.replace("</urlset>", add + "</urlset>", 1)
    open(SITEMAP, "w", encoding="utf-8").write(sm)
    print("sitemap: added", add.count("<url>"), "urls, now", sm.count("<loc>"))
else:
    print("\nslug | title")
    for t in tools:
        print("  /tools/%s | %s" % (t["slug"], t["title"]))
    print("\nDRY RUN - site and sitemap untouched. Check /tmp/toolpages, then run with --apply.")
