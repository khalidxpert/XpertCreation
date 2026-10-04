"""My billers: save a bill's company and reference number, open it in one tap, and get reminded before the due day."""
import re
from datetime import date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Biller

PITC = {"lesco": "LESCO", "iesco": "IESCO", "gepco": "GEPCO", "fesco": "FESCO", "mepco": "MEPCO", "pesco": "PESCO", "tesco": "TESCO",
        "hesco": "HESCO", "sepco": "SEPCO", "qesco": "QESCO"}
OTHER = {"ke": ("K-Electric", "https://www.ke.com.pk"), "sngpl": ("SNGPL (gas)", "https://www.sngpl.com.pk"), "ssgc": ("SSGC (gas)", "https://www.ssgc.com.pk")}
WORLD = {
    "AE": ("United Arab Emirates", {"dewa": ("DEWA (Dubai)", "https://www.dewa.gov.ae"), "sewa": ("SEWA (Sharjah)", "https://www.sewa.gov.ae"),
                                    "addc": ("TAQA / ADDC (Abu Dhabi)", "https://www.addc.ae"), "etisalat": ("e& (Etisalat)", "https://www.etisalat.ae"), "du": ("du", "https://www.du.ae")}),
    "SA": ("Saudi Arabia", {"sec": ("Saudi Electricity (SEC)", "https://www.se.com.sa"), "stc": ("STC", "https://www.stc.com.sa"),
                            "mobily": ("Mobily", "https://www.mobily.com.sa"), "zainsa": ("Zain KSA", "https://sa.zain.com")}),
    "QA": ("Qatar", {"kahramaa": ("Kahramaa", "https://www.km.qa"), "ooredoo": ("Ooredoo", "https://www.ooredoo.qa")}),
    "KW": ("Kuwait", {"mew": ("Ministry of Electricity & Water", "https://www.mew.gov.kw")}),
    "GB": ("United Kingdom", {"britishgas": ("British Gas", "https://www.britishgas.co.uk"), "edf": ("EDF", "https://www.edfenergy.com"),
                              "octopus": ("Octopus Energy", "https://octopus.energy"), "thames": ("Thames Water", "https://www.thameswater.co.uk"), "bt": ("BT", "https://www.bt.com")}),
    "NO": ("Norway", {"fjordkraft": ("Fjordkraft", "https://www.fjordkraft.no"), "tibber": ("Tibber", "https://tibber.com"), "telenor": ("Telenor", "https://www.telenor.no")}),
}
COUNTRIES = [("PK", "Pakistan")] + [(k, v[0]) for k, v in WORLD.items()] + [
    ("US", "United States"), ("CA", "Canada"), ("OM", "Oman"), ("BH", "Bahrain"), ("DE", "Germany"), ("IT", "Italy"), ("ES", "Spain"), ("FR", "France"),
    ("NL", "Netherlands"), ("SE", "Sweden"), ("DK", "Denmark"), ("AU", "Australia"), ("MY", "Malaysia"), ("TR", "Turkey"), ("CN", "China"), ("IN", "India"),
    ("BD", "Bangladesh"), ("AF", "Afghanistan"), ("ZA", "South Africa"), ("XX", "Other country")]
MAX_BILLERS = 15


def companies(country):
    if country == "PK":
        return [{"key": k, "name": v} for k, v in PITC.items()] + [{"key": k, "name": v[0]} for k, v in OTHER.items()]
    return [{"key": k, "name": v[0]} for k, v in WORLD.get(country, ("", {}))[1].items()]


def _preset(c):
    for _, (_, d) in WORLD.items():
        if c in d: return d[c]
    return OTHER.get(c)


def company_name(c, b=None):
    if b is not None and c == "other": return b.label or "Bill"
    if c in PITC: return PITC[c]
    p = _preset(c); return p[0] if p else c.upper()


def bill_link(c, ref, b=None):
    if b is not None and c == "other": return b.link or ""
    if c in PITC:
        return "https://bill.pitc.com.pk/%sbill/general?refno=%s" % (c, ref)
    p = _preset(c); return p[1] if p else "https://xpertcreation.com/bills"


def masked(ref):
    return ref[:4] + " \u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 " + ref[-2:] if len(ref) > 8 else ref


def next_due(day, today=None):
    t = today or date.today(); d = min(day, 28)
    due = date(t.year, t.month, d)
    if due < t:
        due = date(t.year + (t.month == 12), t.month % 12 + 1, d)
    return due


def _out(b):
    nd = next_due(b.due_day)
    return {"id": b.id, "nickname": b.nickname, "company": b.company, "company_name": company_name(b.company, b), "country": b.country, "ref": masked(b.ref),
            "due_day": b.due_day, "next_due": nd.isoformat(), "days_left": (nd - date.today()).days, "remind": b.remind, "link": bill_link(b.company, b.ref, b)}


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def billers(request):
    u = request.user
    if request.method == "GET":
        cc = str(request.GET.get("country") or "PK")[:2].upper()
        return Response({"billers": [_out(b) for b in Biller.objects.filter(user=u).order_by("due_day", "id")],
                         "countries": [{"code": k, "name": v} for k, v in COUNTRIES], "country": cc, "companies": companies(cc)})
    d = request.data
    cc = str(d.get("country") or "PK")[:2].upper(); c = str(d.get("company") or ""); ref = str(d.get("ref") or "").strip(); nick = str(d.get("nickname") or "").strip()[:40]
    label, link = "", ""
    if cc not in dict(COUNTRIES):
        return Response({"detail": "Choose your country."}, status=400)
    if c == "other":
        label = str(d.get("label") or "").strip()[:60]; link = str(d.get("link") or "").strip()[:300]
        if len(label) < 2:
            return Response({"detail": "Type the company name."}, status=400)
        if link and not re.match(r"^https://[^\s]+\.[^\s]+$", link):
            return Response({"detail": "The bill website must start with https://"}, status=400)
    elif c not in [x["key"] for x in companies(cc)]:
        return Response({"detail": "Choose your company."}, status=400)
    if c in PITC:
        ref = re.sub(r"\D", "", ref)
        if len(ref) != 14:
            return Response({"detail": "The reference number on %s bills has 14 digits." % PITC[c]}, status=400)
    ref = re.sub(r"\s+", "", ref)[:24]
    if not (3 <= len(ref) <= 24) or not re.match(r"^[A-Za-z0-9\-/]+$", ref):
        return Response({"detail": "Enter the account or reference number from your bill."}, status=400)
    try:
        day = int(d.get("due_day") or 15)
    except ValueError:
        day = 15
    if Biller.objects.filter(user=u).count() >= MAX_BILLERS:
        return Response({"detail": "You can save up to %d billers." % MAX_BILLERS}, status=400)
    b = Biller.objects.create(user=u, nickname=nick or (label or company_name(c)), company=c, country=cc, label=label, link=link, ref=ref, due_day=max(1, min(28, day)), remind=d.get("remind") is not False)
    return Response(_out(b), status=201)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def biller(request, pk):
    b = Biller.objects.filter(pk=pk, user=request.user).first()
    if not b:
        return Response({"detail": "Not found."}, status=404)
    if request.method == "DELETE":
        b.delete(); return Response({"deleted": True})
    if "remind" in request.data:
        b.remind = bool(request.data.get("remind"))
    if "due_day" in request.data:
        try:
            b.due_day = max(1, min(28, int(request.data.get("due_day"))))
        except (TypeError, ValueError):
            pass
    b.save(); return Response(_out(b))
