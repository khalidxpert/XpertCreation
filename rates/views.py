"""Gold, currency and fuel rates in PKR: currencies fetched every few hours, gold and fuel entered by staff."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Rate, RateDay

CURRENCIES = [("usd", "US Dollar", "\U0001F1FA\U0001F1F8"), ("eur", "Euro", "\U0001F1EA\U0001F1FA"), ("gbp", "British Pound", "\U0001F1EC\U0001F1E7"),
              ("sar", "Saudi Riyal", "\U0001F1F8\U0001F1E6"), ("aed", "UAE Dirham", "\U0001F1E6\U0001F1EA"), ("cad", "Canadian Dollar", "\U0001F1E8\U0001F1E6"),
              ("aud", "Australian Dollar", "\U0001F1E6\U0001F1FA"), ("cny", "Chinese Yuan", "\U0001F1E8\U0001F1F3"), ("kwd", "Kuwaiti Dinar", "\U0001F1F0\U0001F1FC"),
              ("qar", "Qatari Riyal", "\U0001F1F6\U0001F1E6"), ("myr", "Malaysian Ringgit", "\U0001F1F2\U0001F1FE"), ("nok", "Norwegian Krone", "\U0001F1F3\U0001F1F4")]
MANUAL = []   # gold and fuel removed: no one to update them daily (add entries back here to show them again)
MKEYS = {k for k, _, _ in MANUAL}


def is_staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def save_rate(key, value, source):
    v = Decimal(str(value)).quantize(Decimal("0.01"))
    Rate.objects.update_or_create(key=key, defaults={"value": v, "source": source})
    RateDay.objects.update_or_create(key=key, day=timezone.localdate(), defaults={"value": v})


def _hist(key, days=30):
    since = timezone.localdate() - timedelta(days=days)
    return [[d.day.isoformat(), float(d.value)] for d in RateDay.objects.filter(key=key, day__gte=since).order_by("day")]


def _row(key, label, extra, by):
    r = by.get(key)
    h = _hist(key)
    prev = h[-2][1] if len(h) >= 2 else None
    return {"key": key, "label": label, "extra": extra, "value": float(r.value) if r else None, "updated": r.updated_at.isoformat() if r else None,
            "change": round(float(r.value) - prev, 2) if (r and prev is not None) else None, "history": h}


@api_view(["GET"])
@permission_classes([AllowAny])
def rates(request):
    by = {r.key: r for r in Rate.objects.all()}
    return Response({"metals_fuel": [_row(k, l, e, by) for k, l, e in MANUAL],
                     "currencies": [_row(k, l, f, by) for k, l, f in CURRENCIES],
                     "currency_source": "Exchange rates by open.er-api.com (indicative mid-market rates; banks and open market may differ)",
                     "staff": is_staff(request.user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_rates(request):
    if not is_staff(request.user):
        return Response({"detail": "Only staff can update rates."}, status=403)
    done = []
    for k, v in (request.data.get("values") or {}).items():
        if k not in MKEYS or v in ("", None):
            continue
        try:
            d = Decimal(str(v).replace(",", ""))
        except InvalidOperation:
            return Response({"detail": "%s is not a number." % k}, status=400)
        if d <= 0 or d > Decimal("100000000"):
            return Response({"detail": "%s looks wrong." % k}, status=400)
        save_rate(k, d, "XpertCreation team"); done.append(k)
    return Response({"saved": done})
