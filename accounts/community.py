"""Public footer numbers: members, countries, who is online, who joined lately.
Nothing private leaves here - a first name and an initial, a country, how long ago."""
import time

from django.core.cache import cache
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User

ONLINE_SECONDS = 300
CACHE_KEY = "footer_stats_v1"

NAMES = {
    "PK": "Pakistan", "IN": "India", "BD": "Bangladesh", "AF": "Afghanistan",
    "GB": "United Kingdom", "US": "United States", "CA": "Canada", "IE": "Ireland",
    "AE": "UAE", "SA": "Saudi Arabia", "QA": "Qatar", "OM": "Oman", "KW": "Kuwait",
    "BH": "Bahrain", "TR": "Turkey", "EG": "Egypt", "DE": "Germany", "FR": "France",
    "IT": "Italy", "ES": "Spain", "NL": "Netherlands", "SE": "Sweden", "NO": "Norway",
    "AU": "Australia", "NZ": "New Zealand", "MY": "Malaysia", "ID": "Indonesia",
    "PH": "Philippines", "VN": "Vietnam", "CN": "China", "JP": "Japan", "KR": "South Korea",
    "NG": "Nigeria", "KE": "Kenya", "ZA": "South Africa",
}


def flag(code):
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code.upper())


def public_name(u):
    if u.hide_from_leaderboard:
        return "A new member"
    parts = (u.full_name or "").split()
    if not parts:
        return "A new member"
    name = parts[0][:20]
    if len(parts) > 1:
        name += " " + parts[-1][0].upper() + "."
    return name


def ago(dt, now):
    s = max(0, int((now - dt).total_seconds()))
    if s < 120:
        return "just now"
    if s < 3600:
        return "%d minutes ago" % (s // 60)
    if s < 86400:
        h = s // 3600
        return "%d hour%s ago" % (h, "" if h == 1 else "s")
    d = s // 86400
    if d < 60:
        return "%d day%s ago" % (d, "" if d == 1 else "s")
    return "%d months ago" % (d // 30)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def footer_stats(request):
    data = cache.get(CACHE_KEY)
    if data is not None:
        return Response(data)

    now = timezone.now()
    users = list(User.objects.filter(is_active=True, is_blocked=False, is_email_verified=True)
                 .only("id", "full_name", "signup_country", "date_joined", "hide_from_leaderboard")
                 .order_by("-date_joined"))
    seen = cache.get_many(["seen:%d" % u.pk for u in users]) if users else {}
    cutoff = time.time() - ONLINE_SECONDS

    per = {}
    online = 0
    for u in users:
        is_on = (seen.get("seen:%d" % u.pk) or 0) >= cutoff
        online += is_on
        code = (u.signup_country or "").upper()
        if len(code) == 2:
            row = per.setdefault(code, [0, 0])
            row[0] += 1
            row[1] += is_on

    countries = sorted(
        [{"code": c, "flag": flag(c), "name": NAMES.get(c, c), "members": v[0], "online": v[1]}
         for c, v in per.items()],
        key=lambda x: (-x["members"], x["name"]))
    recent = [{"name": public_name(u), "code": (u.signup_country or "").upper(), "flag": flag((u.signup_country or "").upper()),
               "ago": ago(u.date_joined, now)} for u in users[:10]]

    data = {"members": len(users), "online": int(online), "country_count": len(countries),
            "countries": countries, "recent": recent}
    cache.set(CACHE_KEY, data, 60)
    return Response(data)


def online_count():
    """Signed-in, verified members seen in the last five minutes. Shared with /api/where/."""
    ids = User.objects.filter(is_active=True, is_blocked=False,
                              is_email_verified=True).values_list("id", flat=True)
    keys = ["seen:%d" % i for i in ids]
    if not keys:
        return 0
    cutoff = time.time() - ONLINE_SECONDS
    return sum(1 for v in cache.get_many(keys).values() if (v or 0) >= cutoff)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def online_list(request):
    """Who is online right now - for moderators and staff only. Names and countries, never emails."""
    me = request.user
    if not (me.is_staff or getattr(me, "is_moderator", False)):
        return Response({"detail": "Moderators only."}, status=403)
    users = list(User.objects.filter(is_active=True, is_blocked=False, is_email_verified=True)
                 .only("id", "full_name", "signup_country"))
    seen = cache.get_many(["seen:%d" % u.pk for u in users]) if users else {}
    now = time.time()
    rows = []
    for u in users:
        ts = seen.get("seen:%d" % u.pk)
        if ts and ts >= now - ONLINE_SECONDS:
            rows.append({"id": u.pk, "name": (u.full_name or "").strip() or "Member %d" % u.pk,
                         "code": (u.signup_country or "").upper(), "seen": int(now - ts)})
    rows.sort(key=lambda r: r["seen"])
    return Response({"online": rows})
