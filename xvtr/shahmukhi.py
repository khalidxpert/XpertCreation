# Gurmukhi -> Shahmukhi (Pakistani Punjabi script), same rules as js/shahmukhi-1.js
import re
_C = {"ਕ": "ک", "ਖ": "کھ", "ਗ": "گ", "ਘ": "گھ", "ਙ": "ن", "ਚ": "چ", "ਛ": "چھ", "ਜ": "ج", "ਝ": "جھ", "ਞ": "ن", "ਟ": "ٹ", "ਠ": "ٹھ", "ਡ": "ڈ", "ਢ": "ڈھ",
      "ਣ": "ݨ", "ਤ": "ت", "ਥ": "تھ", "ਦ": "د", "ਧ": "دھ", "ਨ": "ن", "ਪ": "پ", "ਫ": "پھ", "ਬ": "ب", "ਭ": "بھ", "ਮ": "م", "ਯ": "ی", "ਰ": "ر", "ਲ": "ل", "ਵ": "و",
      "ੜ": "ڑ", "ਸ": "س", "ਹ": "ہ", "ਸ਼": "ش", "ਖ਼": "خ", "ਗ਼": "غ", "ਜ਼": "ز", "ਫ਼": "ف", "ਲ਼": "ل", "ੲ": "", "ੳ": ""}
_NUK = {"ਸ": "ش", "ਖ": "خ", "ਗ": "غ", "ਜ": "ز", "ਫ": "ف", "ਲ": "ل", "ਕ": "ق"}
_IND = {"ਅ": "ا", "ਆ": "آ", "ਇ": "ا", "ਈ": "ای", "ਉ": "ا", "ਊ": "او", "ਏ": "اے", "ਐ": "اے", "ਓ": "او", "ਔ": "او"}
_AFTER = {"ਅ": "ا", "ਆ": "ا", "ਇ": "ئ", "ਈ": "ئی", "ਉ": "و", "ਊ": "و", "ਏ": "ئے", "ਐ": "ئے", "ਓ": "و", "ਔ": "و"}
_SIGN = {"ਾ": "ا", "ਿ": "", "ੀ": "ی", "ੁ": "", "ੂ": "و", "ੋ": "و", "ੌ": "و"}
_PUN = {"।": "۔", "॥": "۔", "?": "؟", ",": "،", ";": "؛"}
GURMUKHI = re.compile("[਀-੿]")


def _g(ch):
    return bool(ch) and 0x0A00 <= ord(ch) <= 0x0A7F


def to_shahmukhi(s):
    s = str(s or "")
    if not GURMUKHI.search(s):
        return s
    out, i, n = [], 0, len(s)
    def at(k):
        return s[k] if 0 <= k < n else ""
    def end(k):
        c = at(k)
        return not c or not _g(c) or c == "।"
    while i < n:
        ch, nx = s[i], at(i + 1)
        if ch in _C:
            l = _C[ch]
            if nx == "਼" and ch in _NUK:
                l = _NUK[ch]; i += 1
            out.append(l)
        elif ch in _IND:
            prev = at(i - 1); start = not prev or not _g(prev)
            if prev == "ਿ":
                out.append("ی")
            v = _IND[ch] if start else _AFTER[ch]
            if ch in ("ਏ", "ਐ") and not end(i + 1):
                v = v[:-1] + "ی"
            out.append(v)
        elif ch in ("ੇ", "ੈ"):
            out.append("ے" if end(i + 1) else "ی")
        elif ch in _SIGN:
            out.append(_SIGN[ch])
        elif ch in ("ੰ", "ਂ"):
            out.append("ن" if (nx in _C) else "ں")
        elif ch in ("ੱ", "੍", "਼", "ੑ", "ੵ"):
            pass
        elif 0x0A66 <= ord(ch) <= 0x0A6F:
            out.append(chr(0x06F0 + ord(ch) - 0x0A66))
        elif ch in _PUN:
            out.append(_PUN[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)
