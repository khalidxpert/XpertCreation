import json
import logging
import urllib.parse
import urllib.request

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

log = logging.getLogger(__name__)

# open-meteo needs no key and no account, so nothing secret ever reaches the
# browser and there is no quota to protect. The cache is here for speed, not
# for rationing.
FORECAST = "https://api.open-meteo.com/v1/forecast"
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

TTL = 900                    # 15 minutes
GEO_TTL = 60 * 60 * 24 * 30  # a city does not move

# ISO-3166 alpha-2 country code -> a representative city for weather
CAPITALS = {
 "AF":"Kabul","AL":"Tirana","DZ":"Algiers","AD":"Andorra la Vella","AO":"Luanda","AG":"Saint John's",
 "AR":"Buenos Aires","AM":"Yerevan","AU":"Sydney","AT":"Vienna","AZ":"Baku","BS":"Nassau","BH":"Manama",
 "BD":"Dhaka","BB":"Bridgetown","BY":"Minsk","BE":"Brussels","BZ":"Belmopan","BJ":"Porto-Novo","BT":"Thimphu",
 "BO":"La Paz","BA":"Sarajevo","BW":"Gaborone","BR":"Brasilia","BN":"Bandar Seri Begawan","BG":"Sofia",
 "BF":"Ouagadougou","BI":"Gitega","KH":"Phnom Penh","CM":"Yaounde","CA":"Toronto","CV":"Praia","CF":"Bangui",
 "TD":"N'Djamena","CL":"Santiago","CN":"Beijing","CO":"Bogota","KM":"Moroni","CG":"Brazzaville","CD":"Kinshasa",
 "CR":"San Jose","CI":"Yamoussoukro","HR":"Zagreb","CU":"Havana","CY":"Nicosia","CZ":"Prague","DK":"Copenhagen",
 "DJ":"Djibouti","DM":"Roseau","DO":"Santo Domingo","EC":"Quito","EG":"Cairo","SV":"San Salvador",
 "GQ":"Malabo","ER":"Asmara","EE":"Tallinn","SZ":"Mbabane","ET":"Addis Ababa","FJ":"Suva","FI":"Helsinki",
 "FR":"Paris","GA":"Libreville","GM":"Banjul","GE":"Tbilisi","DE":"Berlin","GH":"Accra","GR":"Athens",
 "GD":"Saint George's","GT":"Guatemala City","GN":"Conakry","GW":"Bissau","GY":"Georgetown","HT":"Port-au-Prince",
 "HN":"Tegucigalpa","HU":"Budapest","IS":"Reykjavik","IN":"New Delhi","ID":"Jakarta","IR":"Tehran","IQ":"Baghdad",
 "IE":"Dublin","IL":"Jerusalem","IT":"Rome","JM":"Kingston","JP":"Tokyo","JO":"Amman","KZ":"Astana",
 "KE":"Nairobi","KI":"Tarawa","KW":"Kuwait City","KG":"Bishkek","LA":"Vientiane","LV":"Riga","LB":"Beirut",
 "LS":"Maseru","LR":"Monrovia","LY":"Tripoli","LI":"Vaduz","LT":"Vilnius","LU":"Luxembourg","MG":"Antananarivo",
 "MW":"Lilongwe","MY":"Kuala Lumpur","MV":"Male","ML":"Bamako","MT":"Valletta","MH":"Majuro","MR":"Nouakchott",
 "MU":"Port Louis","MX":"Mexico City","FM":"Palikir","MD":"Chisinau","MC":"Monaco","MN":"Ulaanbaatar",
 "ME":"Podgorica","MA":"Rabat","MZ":"Maputo","MM":"Naypyidaw","NA":"Windhoek","NR":"Yaren","NP":"Kathmandu",
 "NL":"Amsterdam","NZ":"Wellington","NI":"Managua","NE":"Niamey","NG":"Abuja","KP":"Pyongyang","MK":"Skopje",
 "NO":"Oslo","OM":"Muscat","PK":"Lahore","PW":"Ngerulmud","PS":"Ramallah","PA":"Panama City",
 "PG":"Port Moresby","PY":"Asuncion","PE":"Lima","PH":"Manila","PL":"Warsaw","PT":"Lisbon","QA":"Doha",
 "RO":"Bucharest","RU":"Moscow","RW":"Kigali","KN":"Basseterre","LC":"Castries","VC":"Kingstown","WS":"Apia",
 "SM":"San Marino","ST":"Sao Tome","SA":"Riyadh","SN":"Dakar","RS":"Belgrade","SC":"Victoria","SL":"Freetown",
 "SG":"Singapore","SK":"Bratislava","SI":"Ljubljana","SB":"Honiara","SO":"Mogadishu","ZA":"Johannesburg",
 "KR":"Seoul","SS":"Juba","ES":"Madrid","LK":"Colombo","SD":"Khartoum","SR":"Paramaribo","SE":"Stockholm",
 "CH":"Bern","SY":"Damascus","TW":"Taipei","TJ":"Dushanbe","TZ":"Dodoma","TH":"Bangkok","TL":"Dili",
 "TG":"Lome","TO":"Nuku'alofa","TT":"Port of Spain","TN":"Tunis","TR":"Ankara","TM":"Ashgabat","TV":"Funafuti",
 "UG":"Kampala","UA":"Kyiv","AE":"Dubai","GB":"London","US":"New York","UY":"Montevideo","UZ":"Tashkent",
 "VU":"Port Vila","VA":"Vatican City","VE":"Caracas","VN":"Hanoi","YE":"Sanaa","ZM":"Lusaka","ZW":"Harare",
 "HK":"Hong Kong","MO":"Macau","PR":"San Juan",
}


# WMO weather codes, as words. The numbers alone mean nothing to a reader.
CODES = {
    0: ("Clear sky", "01"), 1: ("Mainly clear", "02"), 2: ("Partly cloudy", "03"),
    3: ("Overcast", "04"), 45: ("Fog", "50"), 48: ("Freezing fog", "50"),
    51: ("Light drizzle", "09"), 53: ("Drizzle", "09"), 55: ("Heavy drizzle", "09"),
    56: ("Freezing drizzle", "09"), 57: ("Freezing drizzle", "09"),
    61: ("Light rain", "10"), 63: ("Rain", "10"), 65: ("Heavy rain", "10"),
    66: ("Freezing rain", "13"), 67: ("Freezing rain", "13"),
    71: ("Light snow", "13"), 73: ("Snow", "13"), 75: ("Heavy snow", "13"),
    77: ("Snow grains", "13"), 80: ("Light showers", "09"), 81: ("Showers", "09"),
    82: ("Violent showers", "09"), 85: ("Snow showers", "13"), 86: ("Snow showers", "13"),
    95: ("Thunderstorm", "11"), 96: ("Thunderstorm with hail", "11"),
    99: ("Thunderstorm with hail", "11"),
}


class WeatherThrottle(SimpleRateThrottle):
    scope = "weather"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def _fetch(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + q,
                                 headers={"User-Agent": "XpertCreation/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())


def describe(code):
    return CODES.get(code, ("Unknown", "01"))


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([WeatherThrottle])
def cities(request):
    """?q=lah  - city suggestions while typing."""
    q = (request.GET.get("q") or "").strip()[:60]
    if len(q) < 2:
        return Response({"cities": []})

    ck = "wx:find:" + q.lower()
    hit = cache.get(ck)
    if hit is not None:
        return Response({"cities": hit})

    try:
        raw = _fetch(GEOCODE, {"name": q, "count": 8, "language": "en", "format": "json"})
    except Exception:
        log.exception("City lookup failed for %r", q)
        return Response({"cities": []})

    out = [{
        "name": r.get("name"), "country": r.get("country", ""),
        "admin": r.get("admin1", ""),
        "lat": r.get("latitude"), "lon": r.get("longitude"),
    } for r in (raw.get("results") or [])]
    cache.set(ck, out, GEO_TTL)
    return Response({"cities": out})


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([WeatherThrottle])
def weather(request):
    """
    ?city=Lahore   or   ?lat=31.5&lon=74.3

    Returns now plus five days. Coordinates are rounded to one decimal (about
    11 km) before they are used, so a shared cache entry cannot be traced back
    to where somebody actually is.
    """
    city = (request.GET.get("city") or "").strip()[:60]
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")
    name = city

    if not city and not (lat and lon) and (request.GET.get("auto") or request.GET.get("cc")):
        clat = request.META.get("HTTP_CF_IPLATITUDE")
        clon = request.META.get("HTTP_CF_IPLONGITUDE")
        cc = (request.GET.get("cc") or request.META.get("HTTP_CF_IPCOUNTRY") or "").strip().upper()[:2]
        if clat and clon:
            lat, lon = clat, clon
        else:
            city = CAPITALS.get(cc, "Lahore")
            name = city

    if city:
        gk = "wx:geo:" + city.lower()
        place = cache.get(gk)
        if place is None:
            try:
                raw = _fetch(GEOCODE, {"name": city, "count": 1,
                                       "language": "en", "format": "json"})
            except Exception:
                log.exception("Geocode failed for %r", city)
                return Response({"detail": "Could not reach the weather service."},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)
            rows = raw.get("results") or []
            place = ({"lat": rows[0]["latitude"], "lon": rows[0]["longitude"],
                      "name": rows[0]["name"], "country": rows[0].get("country", "")}
                     if rows else False)
            cache.set(gk, place, GEO_TTL if place else 3600)
        if not place:
            return Response({"detail": "No city by that name."},
                            status=status.HTTP_404_NOT_FOUND)
        lat, lon, name = place["lat"], place["lon"], place["name"]
        country = place["country"]
    elif lat and lon:
        try:
            lat = round(float(lat), 1)
            lon = round(float(lon), 1)
        except ValueError:
            return Response({"detail": "Bad coordinates."},
                            status=status.HTTP_400_BAD_REQUEST)
        country = ""
    else:
        return Response({"detail": "Give a city or coordinates."},
                        status=status.HTTP_400_BAD_REQUEST)

    ck = "wx:v2:%s,%s" % (round(float(lat), 1), round(float(lon), 1))
    hit = cache.get(ck)
    if hit is not None:
        return Response(dict(hit, city=name or hit.get("city"), cached=True))

    try:
        raw = _fetch(FORECAST, {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max,sunrise,sunset",
            "timezone": "auto", "forecast_days": 6,
        })
    except Exception:
        log.exception("Forecast failed for %s,%s", lat, lon)
        return Response({"detail": "Could not reach the weather service."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    cur = raw.get("current") or {}
    desc, icon = describe(cur.get("weather_code"))

    d = raw.get("daily") or {}
    days = []
    for i in range(len(d.get("time", []))):
        dd, di = describe((d.get("weather_code") or [None])[i])
        days.append({
            "date": d["time"][i],
            "max": round((d.get("temperature_2m_max") or [0])[i]),
            "min": round((d.get("temperature_2m_min") or [0])[i]),
            "rain": (d.get("precipitation_probability_max") or [None])[i],
            "description": dd, "icon": di,
            "sunrise": (d.get("sunrise") or [""])[i][-5:],
            "sunset": (d.get("sunset") or [""])[i][-5:],
        })

    out = {
        "city": name or "Your area", "country": country,
        "temp": round(cur.get("temperature_2m", 0)),
        "feels": round(cur.get("apparent_temperature", 0)),
        "humidity": cur.get("relative_humidity_2m"),
        "wind": round(cur.get("wind_speed_10m", 0)),
        "description": desc, "icon": icon,
        "timezone": raw.get("timezone", ""),
        "days": days,
        "cached": False,
    }
    cache.set(ck, out, TTL)
    return Response(out)
