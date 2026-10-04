"""Content checks for Afsanay: a word list (Urdu, Roman Urdu, English), no links or phone numbers, and an AI safety check
(Llama Guard on the site's Cloudflare AI account). Returns (ok, reason)."""
import json
import os
import re
import urllib.request

from django.conf import settings

# Kept short and unambiguous on purpose; the AI check catches the rest.
BAD = ["fuck", "fucking", "shit", "bitch", "bastard", "porn", "nude", "nudes", "xxx", "sex video", "dick", "pussy", "slut", "whore",
       "madarchod", "behenchod", "bhenchod", "benchod", "chutiya", "chutiye", "harami", "haramzada", "kanjar", "randi", "gandu", "lund", "phudi", "bhosdi",
       "مادرچود", "بہنچود", "چوتیا", "حرامزادہ", "کنجر", "رنڈی", "گانڈو", "پھدی", "لن ", "بھوسڑی"]
LINK = re.compile(r"(https?://|www\.|\b[a-z0-9-]+\.(com|pk|net|org|io|me|info|xyz|shop|online)\b)", re.I)
PHONE = re.compile(r"(\+?92|0)\s*3\d{2}[\s-]?\d{7}|\b\d{4}[\s-]?\d{7}\b")
GUARD = "@cf/meta/llama-guard-3-8b"


def _env():
    try:
        return dict(re.findall(r"^(CF_AI_[A-Z_]+)=(.*)$", open(os.path.join(settings.BASE_DIR, ".env")).read(), re.M))
    except Exception:
        return {}


def rules(text):
    t = " " + (text or "").lower() + " "
    for w in BAD:
        if re.search(r"(?<![a-z\u0600-\u06ff])" + re.escape(w.strip()) + r"(?![a-z\u0600-\u06ff])", t):
            return False, "Contains language that is not allowed."
    if LINK.search(text or ""):
        return False, "Links are not allowed in stories and comments."
    if PHONE.search(text or ""):
        return False, "Phone numbers are not allowed in stories and comments."
    return True, ""


def ai(text):
    """True = safe, False = unsafe, None = could not check."""
    e = _env(); acc, tok = (e.get("CF_AI_ACCOUNT_ID") or "").strip(), (e.get("CF_AI_TOKEN") or "").strip()
    if not (acc and tok):
        return None
    try:
        for i in range(0, min(len(text), 12000), 4000):
            req = urllib.request.Request("https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acc, GUARD),
                                         data=json.dumps({"messages": [{"role": "user", "content": text[i:i + 4000]}]}).encode(),
                                         headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json", "User-Agent": "XpertCreation/1.0"})
            d = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
            r = d.get("result") or {}
            out = r.get("response") if isinstance(r, dict) else r
            if isinstance(out, dict):
                if out.get("safe") is False: return False
            elif "unsafe" in str(out).lower():
                return False
        return True
    except Exception:
        return None


def check(text, deep=True):
    ok, why = rules(text)
    if not ok:
        return False, why, "rules"
    if deep:
        s = ai(text)
        if s is False:
            return False, "Flagged by the safety check for review.", "ai"
        if s is None:
            return True, "", "unchecked"
    return True, "", ""
