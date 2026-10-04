"""Bus timings between cities (Daewoo, Niazi and others), kept up to date by staff. Paste many routes at once."""
import re

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Company, Report, Route, Terminal


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def city(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:1].upper() + s[1:].lower() if s else ""


def parse_times(s):
    out = []
    for t in re.findall(r"(\d{1,2})[:.](\d{2})\s*([AaPp][Mm])?", str(s or "")):
        h, m, ap = int(t[0]), int(t[1]), (t[2] or "").lower()
        if ap == "pm" and h < 12: h += 12
        if ap == "am" and h == 12: h = 0
        if 0 <= h < 24 and 0 <= m < 60: out.append("%02d:%02d" % (h, m))
    return sorted(set(out))


def parse_minutes(s):
    s = str(s or "").lower().replace(" ", "")
    m = re.match(r"^(\d+)h(?:(\d+)m?)?$", s) or re.match(r"^(\d+):(\d{2})$", s)
    if m: return int(m.group(1)) * 60 + int(m.group(2) or 0)
    return int(s) if s.isdigit() else 0


def _route(r):
    t = {x.city: {"name": x.name, "map": x.map_url} for x in r.company.terminals.all()}
    return {"id": r.id, "company": r.company.name, "website": r.company.website, "helpline": r.company.helpline, "from": r.from_city, "to": r.to_city,
            "times": r.times, "minutes": r.minutes, "fare": r.fare, "service": r.service, "checked": r.checked.isoformat(),
            "from_terminal": t.get(r.from_city), "to_terminal": t.get(r.to_city)}


@api_view(["GET"])
@permission_classes([AllowAny])
def search(request):
    qs = Route.objects.filter(active=True).select_related("company").prefetch_related("company__terminals")
    f, t = city(request.GET.get("from")), city(request.GET.get("to"))
    cities = sorted(set(Route.objects.filter(active=True).values_list("from_city", flat=True)) | set(Route.objects.filter(active=True).values_list("to_city", flat=True)))
    out = {"cities": cities, "companies": [{"id": c.id, "name": c.name, "website": c.website, "helpline": c.helpline} for c in Company.objects.order_by("name")], "staff": _staff(request.user)}
    if f and t:
        out["routes"] = [_route(r) for r in qs.filter(from_city__iexact=f, to_city__iexact=t)]
    elif f:
        out["to_cities"] = sorted(set(qs.filter(from_city__iexact=f).values_list("to_city", flat=True)))
    if out["staff"] and request.GET.get("all"):
        out["all"] = [_route(r) for r in Route.objects.select_related("company").prefetch_related("company__terminals").order_by("from_city", "to_city", "company__name")]
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def manage(request):
    """Staff. kind=company {name, website, helpline} | terminal {company, city, name, map_url} | bulk {lines} | delete {id}."""
    if not _staff(request.user):
        return Response({"detail": "Staff only."}, status=403)
    d = request.data; kind = d.get("kind")
    if kind == "company":
        name = str(d.get("name") or "").strip()[:60]
        if not name: return Response({"detail": "Add the company name."}, status=400)
        c, _ = Company.objects.update_or_create(name__iexact=name, defaults={"name": name, "website": str(d.get("website") or "")[:300], "helpline": str(d.get("helpline") or "")[:40]})
        return Response({"ok": True, "id": c.id})
    if kind == "terminal":
        c = Company.objects.filter(name__iexact=str(d.get("company") or "").strip()).first()
        if not c: return Response({"detail": "Add the company first."}, status=400)
        Terminal.objects.update_or_create(company=c, city=city(d.get("city")), defaults={"name": str(d.get("name") or "")[:120], "map_url": str(d.get("map_url") or "")[:400]})
        return Response({"ok": True})
    if kind == "delete":
        Route.objects.filter(pk=d.get("id")).delete(); return Response({"ok": True})
    if kind == "bulk":
        done, bad = 0, []
        for n, line in enumerate(str(d.get("lines") or "").splitlines(), 1):
            if not line.strip(): continue
            line = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", line)   # 2,600 -> 2600 before splitting on commas
            p = [x.strip() for x in line.split(",")]
            if len(p) < 4: bad.append("line %d: needs at least company, from, to, times" % n); continue
            c = Company.objects.filter(name__iexact=p[0]).first() or Company.objects.create(name=p[0][:60])
            times = parse_times(p[3])
            if not times: bad.append("line %d: no times found" % n); continue
            fare = int(re.sub(r"\D", "", p[5]) or 0) if len(p) > 5 else 0
            Route.objects.update_or_create(company=c, from_city=city(p[1]), to_city=city(p[2]), service=(p[6] if len(p) > 6 else "")[:40],
                                           defaults={"times": times, "minutes": parse_minutes(p[4]) if len(p) > 4 else 0, "fare": fare, "active": True})
            done += 1
        return Response({"saved": done, "problems": bad})
    return Response({"detail": "Unknown request."}, status=400)


@api_view(["POST"])
@permission_classes([AllowAny])
def report(request, pk):
    r = Route.objects.filter(pk=pk).first()
    if not r: return Response({"detail": "Not found."}, status=404)
    note = str(request.data.get("note") or "").strip()[:300]
    if len(note) < 3: return Response({"detail": "Tell us what is wrong."}, status=400)
    Report.objects.create(route=r, user=request.user if request.user.is_authenticated else None, note=note)
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def terminals(request):
    """Cities with terminals, and the terminals of one city (Daewoo, Niazi; from their official websites)."""
    from django.db.models import Count
    out = {"cities": [{"city": x["city"], "n": x["n"]} for x in Terminal.objects.values("city").annotate(n=Count("id")).order_by("city")]}
    c = city(request.GET.get("city"))
    if c:
        out["terminals"] = [{"company": t.company.name, "website": t.company.website, "helpline": t.company.helpline, "name": t.name, "map": t.map_url}
                            for t in Terminal.objects.filter(city__iexact=c).select_related("company").order_by("company__name", "name")]
    return Response(out)
