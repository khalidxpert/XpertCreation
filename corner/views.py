"""Islamic corner (Ayah of the day from AlQuran Cloud, Hijri date from AlAdhan), recipes, and poetry of the day."""
import json
import os
import secrets
import urllib.request
from datetime import date

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .content import AYAHS, POETRY, RECIPES
from .models import DailyAyah, Recipe

CATS = {"main": "Main dishes", "rice": "Rice", "snack": "Snacks", "sweet": "Sweets", "side": "Sides", "bread": "Breads"}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "XpertCreation/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())


def _ayah(day):
    a = DailyAyah.objects.filter(day=day).first()
    if a:
        return a
    ref = AYAHS[day.toordinal() % len(AYAHS)]
    try:
        d = _get("https://api.alquran.cloud/v1/ayah/%s/editions/quran-uthmani,ur.kanzuliman,en.ahmedraza" % ref)["data"]
        ar, ur, en = d[0], d[1], d[2]
        hj = ""
        try:
            h = _get("https://api.aladhan.com/v1/gToH/%s" % day.strftime("%d-%m-%Y"))["data"]["hijri"]
            hj = "%s %s %s AH" % (h["day"], h["month"]["en"], h["year"])
        except Exception:
            pass
        return DailyAyah.objects.create(day=day, ref=ref, surah="%s (%s)" % (ar["surah"]["englishName"], ar["surah"]["name"]), arabic=ar["text"], urdu=ur["text"], english=en["text"], hijri=hj)
    except Exception:
        return DailyAyah.objects.order_by("-day").first()


_RAM = {}


def _ramadan(today):
    if today in _RAM:
        return _RAM[today]
    _RAM.clear(); _RAM[today] = _ramadan_fetch(today)
    return _RAM[today]


def _ramadan_fetch(today):
    try:
        h = _get("https://api.aladhan.com/v1/gToH/%s" % today.strftime("%d-%m-%Y"))["data"]["hijri"]
        y = int(h["year"]) + (1 if int(h["month"]["number"]) >= 9 else 0)
        g = _get("https://api.aladhan.com/v1/hToG/01-09-%d" % y)["data"]["gregorian"]["date"]
        d = date(int(g[6:10]), int(g[3:5]), int(g[0:2]))
        return {"starts": d.isoformat(), "days": (d - today).days} if d >= today else None
    except Exception:
        return None


@api_view(["GET"])
@permission_classes([AllowAny])
def islamic(request):
    today = timezone.localdate(); a = _ayah(today)
    out = {"friday": today.weekday() == 4, "hijri": a.hijri if a else "", "ramadan": _ramadan(today),
           "source": "Quran text and translations: AlQuran Cloud (Tanzil). Urdu: Kanz-ul-Iman by Imam Ahmed Raza Khan. English: translation of Kanz-ul-Iman. Hijri date: AlAdhan (may differ by a day from the local moon sighting)."}
    if a:
        out["ayah"] = {"ref": a.ref, "surah": a.surah, "arabic": a.arabic, "urdu": a.urdu, "english": a.english, "link": "/quran/%s-%s#a%s" % (a.ref.split(":")[0], __import__("django.utils.text", fromlist=["slugify"]).slugify(a.surah.split(" (")[0]) or "surah", a.ref.split(":")[1])}
    return Response(out)


@api_view(["GET"])
@permission_classes([AllowAny])
def poetry(request):
    today = timezone.localdate(); i = today.toordinal() % len(POETRY)
    pick = lambda p: {"poet": p[0], "text": p[1], "urdu": p[2], "english": p[3]}
    return Response({"today": pick(POETRY[i]), "all": [pick(p) for p in POETRY]})


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _seed():
    if not Recipe.objects.exists():
        for r in RECIPES:
            Recipe.objects.create(approved=True, **r)


def _out(r, full=False):
    o = {"id": r.id, "title": r.title, "category": r.category, "category_name": CATS.get(r.category, r.category), "serves": r.serves, "minutes": r.minutes,
         "intro": r.intro, "photo": (settings.MEDIA_URL.rstrip("/") + "/" + r.photo) if r.photo else "", "by": (getattr(r.author, "full_name", "") or getattr(r.author, "username", "")) if r.author else "XpertCreation kitchen",
         "approved": r.approved}
    if full:
        o.update(ingredients=r.ingredients, steps=r.steps)
    return o


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def recipes(request):
    _seed()
    if request.method == "GET":
        qs = Recipe.objects.filter(approved=True)
        c = request.GET.get("cat"); q = (request.GET.get("q") or "").strip()
        if c in CATS: qs = qs.filter(category=c)
        if q: qs = qs.filter(title__icontains=q)
        out = {"recipes": [_out(r) for r in qs.order_by("-id")[:200]], "cats": CATS}
        if _staff(request.user):
            out["pending"] = [_out(r, True) for r in Recipe.objects.filter(approved=False).order_by("id")[:50]]
        return Response(out)
    if not request.user.is_authenticated:
        return Response({"detail": "Sign in to share a recipe."}, status=401)
    d = request.data
    try:
        ing = json.loads(d.get("ingredients") or "[]") if isinstance(d.get("ingredients"), str) else (d.get("ingredients") or [])
        steps = json.loads(d.get("steps") or "[]") if isinstance(d.get("steps"), str) else (d.get("steps") or [])
    except ValueError:
        return Response({"detail": "Ingredients or steps are not in the right format."}, status=400)
    title = str(d.get("title") or "").strip()[:120]
    ing = [[x[0], str(x[1])[:10], str(x[2])[:80]] for x in ing if isinstance(x, list) and len(x) == 3][:40]
    steps = [str(s).strip()[:500] for s in steps if str(s).strip()][:25]
    if not title or len(ing) < 2 or not steps:
        return Response({"detail": "Add a title, at least two ingredients and the steps."}, status=400)
    r = Recipe(author=request.user, title=title, category=d.get("category") if d.get("category") in CATS else "main", intro=str(d.get("intro") or "")[:300],
               ingredients=ing, steps=steps, serves=max(1, min(20, int(d.get("serves") or 4))), minutes=max(5, min(600, int(d.get("minutes") or 30))))
    f = request.FILES.get("photo")
    if f and f.size <= 6 * 1024 * 1024:
        from PIL import Image, ImageOps
        try:
            im = ImageOps.exif_transpose(Image.open(f)).convert("RGB"); im.thumbnail((1280, 1280))
            rel = "recipes/%s.webp" % secrets.token_hex(10); os.makedirs(os.path.join(settings.MEDIA_ROOT, "recipes"), exist_ok=True)
            im.save(os.path.join(settings.MEDIA_ROOT, rel), "WEBP", quality=82); r.photo = rel
        except Exception:
            pass
    r.approved = _staff(request.user)
    r.save()
    return Response({"id": r.id, "approved": r.approved}, status=201)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
def recipe(request, pk):
    _seed()
    r = Recipe.objects.filter(pk=pk).first()
    if not r or (not r.approved and not _staff(request.user) and (not request.user.is_authenticated or r.author_id != request.user.pk)):
        return Response({"detail": "Recipe not found."}, status=404)
    if request.method == "GET":
        return Response(_out(r, True))
    if not _staff(request.user):
        return Response({"detail": "Only staff can do that."}, status=403)
    if request.method == "DELETE":
        r.delete(); return Response({"deleted": True})
    r.approved = True; r.save(update_fields=["approved"]); return Response({"approved": True})



@api_view(["GET"])
@permission_classes([AllowAny])
def surah(request, n):
    """A whole surah (Arabic, Urdu, English), fetched once from AlQuran Cloud and kept on our server."""
    if not 1 <= n <= 114:
        return Response({"detail": "No such surah."}, status=404)
    path = os.path.join(settings.MEDIA_ROOT, "quran", "%d.json" % n)
    if os.path.exists(path):
        return Response(json.load(open(path, encoding="utf-8")))
    try:
        ar, ur, en = _get("https://api.alquran.cloud/v1/surah/%d/editions/quran-uthmani,ur.kanzuliman,en.ahmedraza" % n)["data"]
    except Exception:
        return Response({"detail": "Could not load this surah right now."}, status=503)
    out = {"number": n, "name": ar["englishName"], "arabic_name": ar["name"],
           "ayahs": [{"n": a["numberInSurah"], "ar": a["text"], "ur": ur["ayahs"][i]["text"], "en": en["ayahs"][i]["text"]} for i, a in enumerate(ar["ayahs"])],
           "source": "Quran text and translations: AlQuran Cloud (Tanzil). Urdu: Kanz-ul-Iman by Imam Ahmed Raza Khan. English: translation of Kanz-ul-Iman."}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return Response(out)
