"""Ads: fair rotation and view/click counting for paid boosts. Payments stay in the shop app."""
import hashlib
import json
import random
import re
import time
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db.models import F, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import AdDailyStat, AdEvent

SALT = "xc-ads-v1"
TOKEN_AGE = 30 * 60     # a token works for 30 minutes
DEDUPE = 30 * 60        # one view and one click per visitor per order every 30 minutes
CAP_PER_DAY = 3         # the same viewer gets a boosted post at the top at most 3 times a day
RATE = 30               # events per visitor per minute
BOTS = re.compile(r"bot|crawl|spider|slurp|preview|headless|lighthouse|curl|wget|python-requests|httpclient", re.I)


def _ip(request):
    m = request.META
    return (m.get("HTTP_X_REAL_IP") or m.get("HTTP_X_FORWARDED_FOR", "").split(",")[0] or m.get("REMOTE_ADDR") or "").strip()


def _visitor(request):
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated:
        return "u%d" % u.pk
    raw = "%s|%s|%s" % (settings.SECRET_KEY[:16], _ip(request), request.META.get("HTTP_USER_AGENT", "")[:200])
    return "g" + hashlib.sha256(raw.encode()).hexdigest()[:31]


def _post_orders():
    """{post id: running post_boost order id}"""
    from shop.models import Order
    now = timezone.now()
    return dict(Order.objects.filter(product="post_boost", status="paid", starts_at__lte=now, ends_at__gt=now)
                .values_list("target_id", "id"))


def pick_boosted(qs, boosted_ids, request, n=3):
    """Up to n boosted posts for the top of For you: random order, and each viewer sees one there
    at most CAP_PER_DAY times a day, so every paid boost gets a fair share."""
    try:
        cands = list(qs.filter(id__in=boosted_ids))
        v, day = _visitor(request), timezone.localdate().isoformat()
        keys = {p.id: "ads:cap:%s:%s:%s" % (day, v, p.id) for p in cands}
        seen = cache.get_many(list(keys.values())) if keys else {}
        cands = [p for p in cands if (seen.get(keys[p.id]) or 0) < CAP_PER_DAY]
        random.shuffle(cands)
        top = cands[:n]
        for p in top:
            k = keys[p.id]
            if not cache.add(k, 1, 86400):
                try:
                    cache.incr(k)
                except ValueError:
                    cache.set(k, 1, 86400)
        return top
    except Exception:
        return list(qs.filter(id__in=boosted_ids).order_by("-id")[:n])


def token_for(post_id, request, placement="feed"):
    """Signed token the page sends back when the boosted post is seen or clicked. "" when not running."""
    try:
        oid = cache.get_or_set("ads:post_orders", _post_orders, 60).get(post_id)
        if not oid:
            return ""
        return signing.dumps({"o": oid, "p": placement, "v": _visitor(request)}, salt=SALT, compress=True)
    except Exception:
        return ""


def _no(why):
    return JsonResponse({"ok": False, "why": why})


def _count(request, kind):
    if request.method != "POST":
        return JsonResponse({"ok": False, "why": "POST only"}, status=405)
    try:
        tok = (json.loads(request.body[:4000].decode() or "{}") or {}).get("t", "")
    except Exception:
        tok = request.POST.get("t", "")
    try:
        d = signing.loads(str(tok), salt=SALT, max_age=TOKEN_AGE)
    except signing.BadSignature:
        return JsonResponse({"ok": False, "why": "bad or old token"}, status=400)
    ua = request.META.get("HTTP_USER_AGENT", "")
    if not ua or BOTS.search(ua):
        return _no("bot")
    v = _visitor(request)
    if d.get("v") != v:
        return _no("token is for another visitor")
    rk = "ads:rl:%s:%d" % (v, int(time.time() // 60))
    if not cache.add(rk, 1, 120):
        try:
            if cache.incr(rk) > RATE:
                return _no("too fast")
        except ValueError:
            cache.set(rk, 1, 120)
    from shop.models import Order
    now = timezone.now()
    o = Order.objects.filter(pk=d.get("o"), status="paid", starts_at__lte=now, ends_at__gt=now).first()
    if not o:
        return _no("not running")
    u = request.user
    if u.is_authenticated and (u.pk == o.user_id or u.is_staff or u.is_superuser):
        return _no("own or staff")
    if not cache.add("ads:dd:%s:%s:%s" % (kind, o.id, v), 1, DEDUPE):
        return _no("already counted")
    AdEvent.objects.create(order=o, kind=kind, placement=str(d.get("p") or "feed")[:20],
                           user=u if u.is_authenticated else None, visitor=v)
    row, _ = AdDailyStat.objects.get_or_create(order=o, day=timezone.localdate())
    AdDailyStat.objects.filter(pk=row.pk).update(**{kind + "s": F(kind + "s") + 1})
    return JsonResponse({"ok": True})


@csrf_exempt
def view(request):
    return _count(request, "view")


@csrf_exempt
def click(request):
    return _count(request, "click")


def stats(request):
    """Views and clicks for the signed-in member's own orders: totals plus the last 30 days."""
    u = request.user
    if not u.is_authenticated:
        return JsonResponse({"detail": "Sign in."}, status=401)
    out = {}
    for r in AdDailyStat.objects.filter(order__user=u).values("order_id").annotate(v=Sum("views"), c=Sum("clicks")):
        out[str(r["order_id"])] = {"views": r["v"] or 0, "clicks": r["c"] or 0, "days": []}
    since = timezone.localdate() - timedelta(days=29)
    for r in AdDailyStat.objects.filter(order__user=u, day__gte=since).order_by("day").values("order_id", "day", "views", "clicks"):
        out.setdefault(str(r["order_id"]), {"views": 0, "clicks": 0, "days": []})["days"].append(
            {"day": r["day"].isoformat(), "views": r["views"], "clicks": r["clicks"]})
    return JsonResponse({"orders": out})
