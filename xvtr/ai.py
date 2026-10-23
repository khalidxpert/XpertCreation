"""Cloudflare Workers AI (the same account as Translate): Whisper turns speech into timed text,
Llama translates the subtitle lines. Keys come from the API .env (CF_AI_ACCOUNT_ID, CF_AI_TOKEN) and are never printed."""
import base64
import json
import os
import re
import urllib.error
import urllib.request

from django.conf import settings

WHISPER = "@cf/openai/whisper-large-v3-turbo"
WHISPER_OLD = "@cf/openai/whisper"
LLM = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

# code: (English name, name in its own script, how the translator should write it)
LANGS = {
    "ur": ("Urdu", "اردو", "Urdu in Urdu script (never Roman Urdu, never Hindi script)"),
    "en": ("English", "English", "English"),
    "pa": ("Punjabi", "پنجابی", "Punjabi in Shahmukhi, the Perso-Arabic script used in Pakistan (never Gurmukhi)"),
    "ar": ("Arabic", "العربية", "Arabic"),
    "hi": ("Hindi", "हिन्दी", "Hindi in Devanagari script"),
    "ps": ("Pashto", "پښتو", "Pashto"),
    "sd": ("Sindhi", "سنڌي", "Sindhi in Arabic script"),
    "fa": ("Persian", "فارسی", "Persian"),
    "bn": ("Bengali", "বাংলা", "Bengali"),
    "tr": ("Turkish", "Türkçe", "Turkish"),
    "de": ("German", "Deutsch", "German"),
    "fr": ("French", "Français", "French"),
    "es": ("Spanish", "Español", "Spanish"),
    "no": ("Norwegian", "Norsk", "Norwegian (Bokmål)"),
    "ru": ("Russian", "Русский", "Russian"),
    "zh": ("Chinese", "中文", "Chinese (Simplified)"),
    "id": ("Indonesian", "Bahasa Indonesia", "Indonesian"),
    "ms": ("Malay", "Bahasa Melayu", "Malay"),
    "it": ("Italian", "Italiano", "Italian"),
    "pt": ("Portuguese", "Português", "Portuguese"),
    "ja": ("Japanese", "日本語", "Japanese"),
    "ko": ("Korean", "한국어", "Korean"),
}
RTL = ("ur", "ar", "pa", "ps", "sd", "fa")


class AIError(Exception):
    pass


def _env():
    try:
        e = dict(re.findall(r"^(CF_AI_[A-Z_]+)=(.*)$", open(os.path.join(str(settings.BASE_DIR), ".env")).read(), re.M))
    except Exception:
        e = {}
    acc = (os.environ.get("CF_AI_ACCOUNT_ID") or e.get("CF_AI_ACCOUNT_ID") or "").strip().strip('"').strip("'")
    tok = (os.environ.get("CF_AI_TOKEN") or e.get("CF_AI_TOKEN") or "").strip().strip('"').strip("'")
    return acc, tok


def ready():
    acc, tok = _env()
    return bool(acc and tok)


def _run(model, payload=None, raw=None, timeout=180):
    acc, tok = _env()
    if not acc or not tok:
        raise AIError("The AI service is not set up on the server.")
    url = getattr(settings, "VTR_AI_URL", "") or "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/" % acc
    body = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(url + model, data=body, headers={
        "Authorization": "Bearer " + tok, "User-Agent": "XpertCreation/1.0",
        "Content-Type": "application/octet-stream" if raw is not None else "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode()[:300]
        except Exception:
            msg = ""
        raise AIError("AI service error %s %s" % (e.code, msg))
    except Exception as e:
        raise AIError("AI service not reachable (%s)" % e.__class__.__name__)
    if isinstance(d, dict) and d.get("success") is False:
        raise AIError("AI service: %s" % (d.get("errors") or "failed"))
    return (d.get("result") if isinstance(d, dict) and "result" in d else d) or {}


def _ts(v):
    """'00:01:02.500' or '01:02.5' or a number -> seconds."""
    if isinstance(v, (int, float)):
        return float(v)
    p = str(v).strip().replace(",", ".").split(":")
    try:
        s = 0.0
        for x in p:
            s = s * 60 + float(x)
        return s
    except ValueError:
        return 0.0


def _from_vtt(vtt):
    out = []
    for blk in re.split(r"\n\s*\n", vtt.replace("\r", "")):
        m = re.search(r"([\d:.,]+)\s*-->\s*([\d:.,]+)[^\n]*\n(.+)", blk, re.S)
        if m:
            t = " ".join(x.strip() for x in m.group(3).split("\n") if x.strip())
            if t:
                out.append({"s": _ts(m.group(1)), "e": _ts(m.group(2)), "t": t})
    return out


def _from_words(words, gap=0.8, most=9.0):
    out, cur = [], None
    for w in words:
        word = str(w.get("word") or w.get("text") or "").strip()
        if not word:
            continue
        s, e = _ts(w.get("start", 0)), _ts(w.get("end", 0))
        if cur and (s - cur["e"] > gap or e - cur["s"] > most or cur["t"].endswith((".", "?", "!", "۔", "؟"))):
            out.append(cur); cur = None
        if not cur:
            cur = {"s": s, "e": e, "t": word}
        else:
            cur["e"] = e; cur["t"] += " " + word
    if cur:
        out.append(cur)
    return out


def segments_of(r, length):
    """The many shapes Whisper can answer with -> [{"s", "e", "t"}] (seconds inside this piece)."""
    segs = []
    for x in (r.get("segments") or []):
        t = str(x.get("text") or "").strip()
        if t:
            segs.append({"s": _ts(x.get("start", 0)), "e": _ts(x.get("end", 0)), "t": t})
    if not segs and r.get("vtt"):
        segs = _from_vtt(r["vtt"])
    if not segs and r.get("words"):
        segs = _from_words(r["words"])
    if not segs and str(r.get("text") or "").strip():
        segs = [{"s": 0.0, "e": float(length), "t": str(r["text"]).strip()}]
    return segs


def transcribe(path, length, lang=None):
    """One piece of sound (an mp3 of up to 2 minutes) -> (segments, detected language)."""
    data = open(path, "rb").read()
    p = {"audio": base64.b64encode(data).decode(), "task": "transcribe", "vad_filter": True, "condition_on_previous_text": False}
    if lang and lang != "auto":
        p["language"] = lang
    try:
        r = _run(WHISPER, p)
    except AIError:
        r = _run(WHISPER_OLD, raw=data)                 # older model: raw bytes in, words with times out
    info = r.get("transcription_info") or {}
    return segments_of(r, length), (info.get("language") or r.get("language") or "")


def translate_lines(lines, to, src=""):
    """A list of subtitle lines -> the same number of lines in another language."""
    if not lines:
        return []
    how = LANGS[to][2]
    numbered = "\n".join("%d|%s" % (i + 1, t.replace("\n", " ")) for i, t in enumerate(lines))
    msgs = [{"role": "system", "content": "You translate video subtitles into %s. Each input line is 'number|text'. "
                                          "Reply with exactly one line per input line, in the same order, as 'number|translation'. "
                                          "Keep names, numbers and links. No notes, no extra lines." % how},
            {"role": "user", "content": numbered}]
    r = _run(LLM, {"messages": msgs, "max_tokens": min(4000, 300 + len(numbered) * 3)}, timeout=120)
    text = str(r.get("response") or "") if isinstance(r, dict) else str(r)
    got = {}
    for ln in text.split("\n"):
        m = re.match(r"\s*(\d+)\s*[|:.)\-]\s*(.*)$", ln)
        if m and m.group(2).strip():
            got[int(m.group(1))] = m.group(2).strip()
    return [got.get(i + 1) for i in range(len(lines))]
