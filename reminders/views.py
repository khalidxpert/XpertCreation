from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DAYS_IN_MONTH, MONTHS, RELATIONS, Birthday

MAX_PER_USER = 300


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


def shape(b):
    return {
        "id": b.id, "name": b.name, "relation": b.relation,
        "day": b.day, "month": b.month, "year": b.year,
        "pretty": b.pretty, "days_away": b.days_away,
        "next": b.next_occurrence().isoformat(),
        "turning": b.turning,
        "phone": b.phone, "email": b.email, "note": b.note,
        "days_before": b.days_before, "remind_on_day": b.remind_on_day,
    }


def read(data, existing=None):
    """Validates and returns field values, or raises ValueError with a message."""
    name = str(data.get("name") or "").strip()[:120]
    if len(name) < 2:
        raise ValueError("Whose birthday is it?")

    try:
        day = int(data.get("day"))
        month = int(data.get("month"))
    except (TypeError, ValueError):
        raise ValueError("Pick a day and a month.")
    if not (1 <= month <= 12):
        raise ValueError("Pick a month.")
    if not (1 <= day <= DAYS_IN_MONTH[month - 1]):
        raise ValueError("%s does not have %d days." % (MONTHS[month - 1][1], day))

    year = data.get("year")
    if year in ("", None):
        year = None
    else:
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise ValueError("Year: enter four digits, or leave it blank.")
        this_year = timezone.localdate().year
        if not (1900 <= year <= this_year):
            raise ValueError("Year: between 1900 and %d, or leave it blank." % this_year)

    relation = data.get("relation")
    if relation not in dict(RELATIONS):
        relation = "friend"

    phone = str(data.get("phone") or "").strip().replace(" ", "")[:20]
    if phone and not (phone.startswith("+") and phone[1:].isdigit()):
        raise ValueError("Phone: use international format, e.g. +923001234567.")

    days_before = data.get("days_before", 3)
    try:
        days_before = max(0, min(30, int(days_before)))
    except (TypeError, ValueError):
        days_before = 3

    return dict(
        name=name, relation=relation, day=day, month=month, year=year,
        phone=phone, email=str(data.get("email") or "").strip()[:200],
        note=str(data.get("note") or "").strip()[:300],
        days_before=days_before,
        remind_on_day=bool(data.get("remind_on_day", True)),
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def birthdays(request):
    if request.method == "GET":
        rows = sorted(Birthday.objects.filter(owner=request.user),
                      key=lambda b: b.days_away)
        today = [shape(b) for b in rows if b.days_away == 0]
        soon = [shape(b) for b in rows if 0 < b.days_away <= 30]
        return Response({
            "today": today, "soon": soon,
            "all": [shape(b) for b in rows],
            "count": len(rows),
            "months": [{"value": v, "label": l} for v, l in MONTHS],
            "relations": [{"value": v, "label": l} for v, l in RELATIONS],
        })

    if Birthday.objects.filter(owner=request.user).count() >= MAX_PER_USER:
        return _err("You have reached the limit of %d saved birthdays." % MAX_PER_USER)

    try:
        fields = read(request.data)
    except ValueError as exc:
        return _err(str(exc))

    b = Birthday.objects.create(owner=request.user, **fields)
    return Response(shape(b), status=status.HTTP_201_CREATED)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def birthday(request, pk):
    b = Birthday.objects.filter(id=pk, owner=request.user).first()
    if not b:
        return _err("Not found.", code=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        b.delete()
        return Response({"detail": "Removed."})

    if request.method == "GET":
        return Response(shape(b))

    try:
        fields = read(request.data, existing=b)
    except ValueError as exc:
        return _err(str(exc))

    for k, v in fields.items():
        setattr(b, k, v)
    b.save()
    return Response(shape(b))
