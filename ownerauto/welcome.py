"""The welcome email: a short note from the founder and one line + link for every part of XpertCreation."""
import html
import re
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

log = logging.getLogger(__name__)
SITE = "https://xpertcreation.com"
APP = "https://play.google.com/store/apps/details?id=com.xpertcreation.app"

# (emoji, name, one line, Urdu line, link)
PARTS = [
    ("Connect & earn", [
        ("\U0001F91D", "XpertConnect", "Pakistan's own social network: post, follow, go live and grow your network.", "اپنا نیٹ ورک بنائیں", "/feed"),
        ("\U0001F4AC", "XpertChat", "Chats, groups and channels, stickers, voice notes, and free voice and video calls.", "مفت چیٹ اور وائس / ویڈیو کال", "/chat"),
        ("\U0001F3A5", "XpertMeet", "Online meetings with a link, raise hand, reactions and an invitation with the time in 15 countries.", "آن لائن میٹنگ، مفت", "/call"),
        ("\U0001F534", "Go Live", "Go live from your phone; your followers get a notification and can comment.", "اپنے فون سے لائیو جائیں", "/live"),
        ("\U0001F9D1‍\U0001F4BB", "XpertFreelance", "Sell your skills or hire designers, developers, writers and tutors.", "اپنا ہنر بیچیں", "/market"),
        ("\U0001F4BC", "XpertJobs", "Private jobs, government jobs, results and scholarships.", "نوکری تلاش کریں", "/jobs"),
        ("\U0001F3E2", "Company pages", "Put your business on XpertConnect with a verified company page.", "اپنی کمپنی کا پیج بنائیں", "/companies"),
    ]),
    ("Buy & sell", [
        ("\U0001F6CD️", "XpertStore", "Shop online, or open your own shop free and sell across Pakistan.", "اپنی دکان مفت کھولیں", "/store"),
        ("\U0001F354", "Food delivery", "Order from restaurants and home kitchens near you. Restaurants join free.", "کھانا گھر بیٹھے منگوائیں", "/food"),
        ("\U0001F697", "XpertWheels", "Buy and sell cars and bikes. Free ads, buyers call you directly.", "گاڑی اور بائیک خریدیں یا بیچیں", "/wheels"),
        ("\U0001F3E0", "XpertProperty", "Houses, flats, plots and shops to buy, sell or rent.", "مکان، فلیٹ یا پلاٹ", "/market#property"),
        ("\U0001F6E0️", "XpertPros", "Hire ID-verified plumbers, electricians, AC technicians and more. Pay the worker directly.", "قابلِ اعتماد کاریگر بلائیں", "/pros"),
        ("\U0001F3E8", "Hotels & Tours", "Book hotels, guest houses and tour packages free, and pay at the hotel.", "ہوٹل اور ٹور بک کریں", "/hotels"),
    ]),
    ("Learn & grow", [
        ("\U0001F393", "XpertAcademy", "{C} free courses with certificates: Office, programming, languages, IELTS and skills for work.", "مفت کورسز اور سرٹیفکیٹ", "/academy/"),
        ("\U0001F9EE", "{N} free tools", "Tax, loan, BMI, Zakat, Faraid calculators, legal documents and many handy tools.", "{NU} مفت ٹولز", "/tools"),
        ("\U0001F3AC", "Video Translate", "Subtitles and a transcript for your video, translated into Urdu and 20+ languages.", "ویڈیو کے سب ٹائٹل کسی بھی زبان میں", "/video-translate"),
        ("\U0001F310", "Translate & voice typing", "Translate between Urdu, English, Arabic and more, and speak to type in Urdu.", "بول کر اردو لکھیں", "/translate"),
        ("\U0001F916", "AI Assistant", "Ask about studies, Excel, writing and more, in Urdu or English.", "مفت اے آئی مددگار", "/assistant"),
        ("\U0001FAAA", "Digital business card", "Make a free digital visiting card and share it with a link or QR code.", "ڈیجیٹل وزیٹنگ کارڈ", "/cards"),
    ]),
    ("Family & community", [
        ("\U0001F48D", "Halal Rishta", "Find a rishta the halal way, with your family. Verified members only.", "حلال رشتہ", "/rishta"),
        ("\U0001F333", "Roots of Love", "Build your family tree together with your whole family.", "اپنا خاندانی شجرہ بنائیں", "/roots"),
        ("\U0001F54C", "Islamic corner", "Ayah of the day, the Holy Quran with Urdu translation, the Hijri date and Islamic tools.", "قرآن پاک اور اسلامی ٹولز", "/islamic"),
        ("\U0001F465", "Meetups", "Meet people in your city who like what you like.", "اپنے شہر کے لوگوں سے ملیں", "/meetups"),
        ("\U0001FA78", "Blood Bank", "Give blood, save a life. Find a donor near you in minutes.", "خون دیں، زندگی بچائیں", "/blood"),
        ("\U0001F43E", "Pets", "Your pet's profile, a QR tag for lost pets, adoption and vets.", "اپنے پالتو جانور کا خیال", "/pets"),
        ("\U0001F9F8", "Kids", "Safe cartoons, rhymes, stories and learning videos for children, picked by our team.", "بچوں کے لیے محفوظ کارٹون اور کہانیاں", "/kids"),
    ]),
    ("Everyday", [
        ("\U0001F4A1", "Electricity & gas bills", "Check your electricity or gas bill in seconds.", "بجلی اور گیس کا بل چیک کریں", "/bills"),
        ("\U0001F4B0", "Money", "Keep track of cash, mobile wallets and bank balances, on all your devices.", "اپنے پیسوں کا حساب رکھیں", "/money"),
        ("\U0001F4BC", "My Briefcase", "Keep your degrees, ID card and passport safe, with a reminder before they expire.", "اپنے کاغذات محفوظ رکھیں", "/briefcase"),
        ("\U0001F4C4", "XpertScan", "Scan papers and ID cards with your phone into a clean PDF.", "فون سے اسکین کر کے پی ڈی ایف", "/scan"),
        ("\U0001F698", "Ladies rides", "Safe rides by women drivers, for women: car, rickshaw or bike.", "خواتین کے لیے محفوظ سفر", "/rides"),
        ("\U0001F45F", "Step counter", "Count your steps and see your walk on a live map.", "قدم گنیں، صحت مند رہیں", "/steps"),
        ("\U0001F3AC", "XpertClips & XpertCam", "Watch and share short videos, and take photos with fun filters.", "مختصر ویڈیوز اور فلٹرز", "/clips"),
        ("\U0001F3CF", "News & Sports", "Live cricket scores and the latest news.", "لائیو کرکٹ اسکور", "/sports"),
        ("\U0001F3AE", "Games", "Ludo, carrom, chess and football with friends, free in your browser.", "دوستوں کے ساتھ کھیلیں", "/games"),
        ("\U0001F382", "Birthday Reminders", "Never forget a birthday again.", "سالگرہ کبھی نہ بھولیں", "/birthdays"),
        ("\U0001F4F6", "Nearby chat", "Chat and share with people around you, even without internet.", "بغیر انٹرنیٹ کے قریب لوگوں سے بات کریں", "/nearby"),
        ("\U0001F381", "Rewards", "Use XpertCreation, earn points and spin the lucky wheel.", "پوائنٹس کمائیں", "/rewards"),
    ]),
]

def _courses():
    """How many courses XpertAcademy has right now."""
    try:
        h = open("/var/www/xpertacademy/index.html", encoding="utf-8").read()
        n = len(re.findall(r'\n  \{\n    "id": "[\w-]+",\n    "name"', h))
    except Exception:
        n = 0
    return str(n if n >= 10 else 30)


def _tools():
    """How many tools the Tools page has right now (so the email is never out of date)."""
    import re
    try:
        n = len(re.findall(r'\{\s*id:\s*"[\w-]+",\s*g:', open("/var/www/xpertcreation-landing/tools.html", encoding="utf-8").read()))
    except Exception:
        n = 0
    n = n or 100
    return str(n), str(n).translate(str.maketrans("0123456789", "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"))


def _name(u):
    n = (getattr(u, "full_name", "") or "").strip() or (u.first_name if hasattr(u, "first_name") else "") or u.username or ""
    return n.split(" ")[0][:30] or "there"


def build(u):
    name = _name(u)
    e = html.escape
    rows = ""
    text = ["Assalam o Alaikum %s,\n" % name,
            "Welcome to XpertCreation! I am Syed Khalid Hussain Shah, the founder. We built XpertCreation so that everything you need is in one free account, made in Pakistan.",
            "Here is what you can do with it:\n"]
    N, NU = _tools()
    C = _courses()
    for title, items in PARTS:
        rows += '<tr><td style="padding:18px 0 6px;font-size:13px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#1B4DFF">%s</td></tr>' % e(title)
        text.append("\n" + title.upper())
        for em, nm, line, ur, link in items:
            nm, ur = nm.replace("{N}", N), ur.replace("{NU}", NU)
            line = line.replace("{C}", C)
            url = SITE + link
            rows += ('<tr><td style="padding:6px 0"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#F6F7FB;border:1px solid #E4E8F2;border-radius:14px">'
                     '<tr><td width="48" style="padding:12px 0 12px 14px;font-size:26px;vertical-align:top">%s</td>'
                     '<td style="padding:12px 10px;vertical-align:top"><b style="font-size:15.5px;color:#0D1424">%s</b><br><span style="font-size:14px;color:#5A657C;line-height:1.45">%s</span>'
                     '<br><span style="font-size:13px;color:#5A657C;direction:rtl">%s</span></td>'
                     '<td width="80" style="padding:12px 14px 12px 0;text-align:right;vertical-align:middle"><a href="%s" style="display:inline-block;background:#1B4DFF;color:#fff;text-decoration:none;font-weight:800;font-size:13px;padding:8px 12px;border-radius:10px">Open</a></td></tr></table></td></tr>'
                     % (em, e(nm), e(line), e(ur), e(url)))
            text.append("%s %s - %s\n   %s" % (em, nm, line, url))
    body = """<!doctype html><html><body style="margin:0;background:#EEF1F7;font-family:Inter,Segoe UI,Arial,sans-serif;color:#0D1424">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#EEF1F7"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-radius:20px;overflow:hidden">
<tr><td style="background:#ffffff;padding:26px 26px 20px;color:#0D1424;border-bottom:4px solid #1B4DFF">
<table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="vertical-align:middle"><a href="https://xpertcreation.com" target="_blank" style="text-decoration:none"><img src="https://xpertcreation.com/brand/logo-128.png" width="52" height="52" alt="XpertCreation" style="display:block;border:0;border-radius:14px;width:52px;height:52px"></a></td><td style="padding-left:12px;vertical-align:middle;font-size:20px;font-weight:900"><a href="https://xpertcreation.com" target="_blank" style="color:#0D1424;text-decoration:none">XpertCreation</a></td></tr></table><div style="font-size:28px;font-weight:900;line-height:1.15;margin-top:14px;color:#0D1424">Welcome, %(name)s! \U0001F44B</div>
<div style="font-size:15px;color:#5A657C;margin-top:6px">One free account for everything you need.</div><div style="font-size:16px;margin-top:4px;direction:rtl;text-align:left;color:#1B4DFF">ایک ایپ، ہر ضرورت، ایک ہی جگہ</div></td></tr>
<tr><td style="padding:22px 26px 6px;font-size:15px;line-height:1.6">Assalam o Alaikum %(name)s,<br><br>I am <b>Syed Khalid Hussain Shah</b>, founder of XpertCreation. Thank you for joining. We built XpertCreation in Lahore so that your network, work, shopping, learning and family can all live in one free account.<br><br>Here is a quick look at what you can do:</td></tr>
<tr><td style="padding:0 26px"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0">%(rows)s</table></td></tr>
<tr><td style="padding:20px 26px"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#0D1424;border-radius:16px"><tr><td style="padding:18px;color:#fff;font-size:15px"><b>\U0001F4F1 Get the Android app</b><br><span style="opacity:.85;font-size:14px">Everything on your phone, with notifications.</span></td>
<td style="padding:18px;text-align:right"><a href="%(app)s" style="display:inline-block;background:#F59E0B;color:#111;text-decoration:none;font-weight:900;padding:10px 14px;border-radius:10px">Google Play</a></td></tr></table></td></tr>
<tr><td style="padding:0 26px 22px;font-size:15px;line-height:1.6">Start with your profile so people can find you: <a href="%(site)s/me-profile" style="color:#1B4DFF;font-weight:800">complete your profile</a>. If you need anything, just reply to me on WhatsApp.<br><br>Welcome to the family,</td></tr>
<tr><td style="padding:0 26px 24px;border-top:1px solid #E4E8F2"><div style="height:16px"></div><table cellpadding="0" cellspacing="0" border="0" style="font-family:Arial,Helvetica,sans-serif;color:#0D1424;font-size:13px;line-height:1.5;border-collapse:collapse">
  <tr>
    <td style="padding:0 14px 0 0;vertical-align:top;border-right:3px solid #1B4DFF">
      <a href="https://xpertcreation.com" target="_blank"><img src="https://xpertcreation.com/brand/icon-180.png" width="72" height="72" alt="XpertCreation" style="display:block;border:0;border-radius:14px;width:72px;height:72px"></a>
      <a href="https://xpertcreation.com/feed" target="_blank"><img src="https://xpertcreation.com/brand/sig-xpertconnect-96.png?v=2" width="48" height="48" alt="XpertConnect" title="XpertConnect" style="display:block;border:0;width:48px;height:48px;margin:10px auto 0"></a>
      <div style="font-size:10px;font-weight:bold;color:#1B4DFF;text-align:center;margin-top:2px">XpertConnect</div>
      <a href="https://xpertcreation.com/market" target="_blank"><img src="https://xpertcreation.com/brand/sig-freelance-96.png" width="44" height="44" alt="Freelance" title="Freelance marketplace" style="display:block;border:0;width:44px;height:44px;margin:10px auto 0;border-radius:10px"></a>
      <div style="font-size:10px;font-weight:bold;color:#16A34A;text-align:center;margin-top:2px">Freelance</div>
    </td>
    <td style="padding:0 0 0 14px;vertical-align:top">
      <div style="font-size:16px;font-weight:bold;color:#0D1424">Syed Khalid Hussain Shah</div>
      <div style="font-size:13px;color:#1B4DFF;font-weight:bold">Founder &amp; CEO, XpertCreation</div>
      <div style="font-size:12px;color:#5A657C;margin:4px 0 6px;max-width:380px">Free learning, tools, jobs and community for everyone, worldwide &mdash; XpertAcademy courses, XpertConnect networking and everyday tools, all in one place.</div>
      <div style="font-size:12.5px;color:#0D1424">
        &#128222; <a href="https://wa.me/923009462916" target="_blank" style="color:#0D1424;text-decoration:none">+92 300 946 2916</a> (WhatsApp)<br>
        &#9993;&#65039; <a href="mailto:khalid@xpertcreation.com" style="color:#0D1424;text-decoration:none">khalid@xpertcreation.com</a><br>
        &#127760; <a href="https://xpertcreation.com" target="_blank" style="color:#1B4DFF;text-decoration:none;font-weight:bold">xpertcreation.com</a>
        &nbsp;&middot;&nbsp; <a href="https://xpertcreation.com/in/khalidxpert" target="_blank" style="color:#1B4DFF;text-decoration:none">XpertConnect profile</a><br>
        &#128205; <a href="https://share.google/dlldq7AKwKRjijusO" target="_blank" style="color:#1B4DFF;text-decoration:none">Find us on Google</a> (Lahore, Pakistan)
      </div>
      <table cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;border-collapse:separate">
        <tr>
          <td bgcolor="#1877F2" style="background:#1877F2;border-radius:8px;padding:6px 12px">
            <a class="xsb" href="https://www.facebook.com/groups/1202505063279206" target="_blank" style="color:#ffffff;text-decoration:none;font-size:12px;font-weight:bold;font-family:Arial,Helvetica,sans-serif"><span style="font-family:Georgia,serif;font-size:14px">f</span>&nbsp; Facebook group</a>
          </td>
          <td width="6" style="width:6px;font-size:0">&nbsp;</td>
          <td bgcolor="#7C3AED" style="background:#7C3AED;border-radius:8px;padding:6px 12px">
            <a class="xsb" href="https://xpertcreation.com/chat-rooms" target="_blank" style="color:#ffffff;text-decoration:none;font-size:12px;font-weight:bold;font-family:Arial,Helvetica,sans-serif">#&nbsp; IRC chat rooms</a>
          </td>
          <td width="6" style="width:6px;font-size:0">&nbsp;</td>
          <td bgcolor="#ffffff" style="background:#ffffff;border:2px solid #1B4DFF;border-radius:8px;padding:4px 10px">
            <a class="xsb" href="https://xpertcreation.com/feed" target="_blank" style="color:#1B4DFF;text-decoration:none;font-size:12px;font-weight:bold;font-family:Arial,Helvetica,sans-serif"><img src="https://xpertcreation.com/brand/sig-xpertconnect-32.png?v=2" width="18" height="18" alt="" style="border:0;width:18px;height:18px;vertical-align:-4px">&nbsp;XpertConnect</a>
          </td>
        </tr>
      </table>
      <div style="font-size:11px;color:#5A657C;margin-top:5px">IRC: <a href="https://xpertcreation.com/irc" target="_blank" style="color:#5A657C">xpertcreation.com/irc</a> &middot; mIRC: irc.xpertcreation.com, port 6697 (SSL)</div>
    </td>
  </tr>
</table></td></tr>
<tr><td style="background:#F6F7FB;padding:14px 26px;font-size:12px;color:#5A657C">You get this email once, because you joined XpertCreation. XpertCreation, Lahore, Pakistan.</td></tr>
</table></td></tr></table></body></html>""" % {"name": e(name), "rows": rows, "app": APP, "site": SITE}
    text.append("\nGet the Android app: %s\nComplete your profile: %s/me-profile\n" % (APP, SITE))
    text.append("Welcome to the family,\nSyed Khalid Hussain Shah\nFounder & CEO, XpertCreation\nxpertcreation.com | WhatsApp +92 300 946 2916 | khalid@xpertcreation.com")
    return "Welcome to XpertCreation, %s! \U0001F44B" % name, "\n".join(text), body


def send_welcome(u, to=None):
    subject, text, body = build(u)
    msg = EmailMultiAlternatives(subject=subject, body=text, from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None), to=[to or u.email],
                                 reply_to=["khalid@xpertcreation.com"])
    msg.attach_alternative(body, "text/html")
    try:
        msg.send(fail_silently=False)
        return True
    except Exception:
        log.exception("welcome email to %s failed", to or u.email)
        return False
