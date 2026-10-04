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
MAX_BILLERS = 15


def company_name(c):
    return PITC.get(c) or OTHER.get(c, (c.upper(), ""))[0]


def bill_link(c, ref):
    if c in PITC:
        return "https://bill.pitc.com.pk/%sbill/general?refno=%s" % (c, ref)
    return OTHER.get(c, ("", "https://xpertcreation.com/bills"))[1]


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
    return {"id": b.id, "nickname": b.nickname, "company": b.company, "company_name": company_name(b.company), "ref": masked(b.ref),
            "due_day": b.due_day, "next_due": nd.isoformat(), "days_left": (nd - date.today()).days, "remind": b.remind, "link": bill_link(b.company, b.ref)}


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def billers(request):
    u = request.user
    if request.method == "GET":
        return Response({"billers": [_out(b) for b in Biller.objects.filter(user=u).order_by("due_day", "id")],
                         "companies": [{"key": k, "name": v} for k, v in PITC.items()] + [{"key": k, "name": v[0]} for k, v in OTHER.items()]})
    d = request.data
    c = str(d.get("company") or ""); ref = re.sub(r"\D", "", str(d.get("ref") or "")); nick = str(d.get("nickname") or "").strip()[:40]
    if c not in PITC and c not in OTHER:
        return Response({"detail": "Choose your company."}, status=400)
    if c in PITC and len(ref) != 14:
        return Response({"detail": "The reference number on %s bills has 14 digits." % PITC[c]}, status=400)
    if not (6 <= len(ref) <= 24):
        return Response({"detail": "Enter the reference or consumer number from your bill."}, status=400)
    try:
        day = int(d.get("due_day") or 15)
    except ValueError:
        day = 15
    if Biller.objects.filter(user=u).count() >= MAX_BILLERS:
        return Response({"detail": "You can save up to %d billers." % MAX_BILLERS}, status=400)
    b = Biller.objects.create(user=u, nickname=nick or company_name(c), company=c, ref=ref, due_day=max(1, min(28, day)), remind=d.get("remind") is not False)
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
