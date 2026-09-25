"""
Where members are, and how many are about.

Counts and countries only - never who. A list of who is online tells anyone
watching which women on the blood bank are awake, who is away from home, and
who keeps odd hours. The big platforms stopped showing that for good reasons.
"""
import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

log = logging.getLogger(__name__)
User = get_user_model()

TTL = 300           # five minutes
ONLINE_WINDOW = 15  # minutes

# Two-letter code to name and flag. The flag is built from regional indicator
# characters, so no image files and nothing to keep up to date.
NAMES = {
    "PK": "Pakistan", "IN": "India", "BD": "Bangladesh", "AE": "UAE",
    "SA": "Saudi Arabia", "GB": "United Kingdom", "US": "United States",
    "CA": "Canada", "AU": "Australia", "MY": "Malaysia", "ID": "Indonesia",
    "TR": "Türkiye", "EG": "Egypt", "DE": "Germany", "FR": "France",
    "IT": "Italy", "ES": "Spain", "NL": "Netherlands", "SE": "Sweden",
    "NO": "Norway", "QA": "Qatar", "KW": "Kuwait", "OM": "Oman",
    "BH": "Bahrain", "JO": "Jordan", "LK": "Sri Lanka", "NP": "Nepal",
    "AF": "Afghanistan", "IR": "Iran", "CN": "China", "JP": "Japan",
    "KR": "South Korea", "SG": "Singapore", "TH": "Thailand", "PH": "Philippines",
    "ZA": "South Africa", "NG": "Nigeria", "KE": "Kenya", "BR": "Brazil",
    "MX": "Mexico", "RU": "Russia", "UA": "Ukraine", "PL": "Poland",
    "NZ": "New Zealand", "IE": "Ireland", "CH": "Switzerland", "BE": "Belgium",
    "AT": "Austria", "DK": "Denmark", "FI": "Finland", "PT": "Portugal",
    "GR": "Greece", "CZ": "Czechia", "RO": "Romania", "HU": "Hungary",
}


def flag(code):
    """Two letters to a flag emoji. 'PK' becomes the Pakistan flag."""
    if not code or len(code) != 2 or not code.isalpha():
        return "\U0001F3F3\uFE0F"          # white flag, for unknown
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def country_of(request):
    """
    Cloudflare puts the country in a header on every request, so there is no
    lookup to make, no third party to ask, and no IP address to store.
    """
    code = (request.META.get("HTTP_CF_IPCOUNTRY") or "").upper()
    if code in ("XX", "T1", ""):           # unknown, or Tor
        return None
    return code if len(code) == 2 and code.isalpha() else None


class GeoThrottle(SimpleRateThrottle):
    scope = "geo"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([GeoThrottle])
def where(request):
    """
    Totals by country, plus the caller's own flag.

    No names, no rows about individuals. Countries with fewer than three
    members are folded into "elsewhere": in a country with two members,
    naming it is close to naming them.
    """
    mine = country_of(request)
    out = {"you": None}
    if mine:
        out["you"] = {"code": mine, "flag": flag(mine),
                      "name": NAMES.get(mine, mine)}

    hit = cache.get("geo:summary")
    if hit is None:
        rows = (User.objects.filter(is_active=True, is_blocked=False, is_email_verified=True)
                .exclude(signup_country="")
                .values("signup_country")
                .annotate(n=Count("id")).order_by("-n"))

        listed, folded, countries = [], 0, 0
        for r in rows:
            code = (r["signup_country"] or "").upper()[:2]
            if not code:
                continue
            countries += 1
            if r["n"] < 1:   # every country shown, PenFlow style (was < 3)
                folded += r["n"]
                continue
            listed.append({"code": code, "flag": flag(code),
                           "name": NAMES.get(code, code), "members": r["n"]})

        total = User.objects.filter(is_active=True, is_blocked=False, is_email_verified=True).count()

        hit = {"countries": listed[:24], "country_count": countries,
               "elsewhere": folded, "members": total}
        cache.set("geo:summary", hit, TTL)

    out.update(hit)

    # Same presence as the footer: signed-in members seen in the last five minutes.
    from accounts.community import online_count
    out["online"] = online_count()

    return Response(out)
