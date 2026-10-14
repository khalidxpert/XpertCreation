"""Find people you know.
- A member picks contacts on their phone (or types emails and numbers) and we say which of them are on XpertCreation.
- If they tick "remember my contacts", each email / number is kept only as a one-way scrambled code, so when one of
  those people joins later the member gets a notification ("Ali from your contacts just joined"). Delete any time.
- People you may know: contacts, friends of friends, same city, same company.
Only members who allow it can be found, and the number of checks per day is limited so nobody can trawl."""
import hashlib
import hmac
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ContactHash, FindSetting, JoinTold

User = get_user_model()
MAX_PER_CHECK = 300
CHECKS_PER_DAY = 5
MAX_KEPT = 3000
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,24}$", re.I)


def _digits(p):
    """Last 10 digits of a phone number, so 0300-1234567, +92 300 1234567 and 923001234567 all match."""
    d = re.sub(r"\D", "", str(p or ""))
    return d[-10:] if len(d) >= 10 else ""


def _h(kind, value):
    return hmac.new(settings.SECRET_KEY.encode(), ("%s:%s" % (kind, value)).encode(), hashlib.sha256).hexdigest()


def _phone_map():
    """last-10-digits -> user id, from the phone and WhatsApp numbers members put on their profiles."""
    m = cache.get("find:phones")
    if m is not None:
        return m
    m = {}
    try:
        from network.models import ProProfile
        for uid, socials in ProProfile.objects.values_list("user_id", "socials"):
            if isinstance(socials, dict):
                for k, v in socials.items():
                    if any(w in str(k).lower() for w in ("whatsapp", "phone", "signal", "telegram")):
                        d = _digits(v)
                        if d:
                            m[d] = uid
    except Exception:
        pass
    for f in ("phone", "phone_number", "mobile"):
        if any(x.name == f for x in User._meta.get_fields()):
            for uid, ph in User.objects.exclude(**{f: ""}).exclude(**{f + "__isnull": True}).values_list("id", f):
                d = _digits(ph)
                if d:
                    m[d] = uid
    cache.set("find:phones", m, 600)
    return m


def _card(u, why=""):
    try:
        from network.models import ProProfile
        p = ProProfile.objects.filter(user=u).first()
    except Exception:
        p = None
    try:
        from network.views import _av
        av = _av(u) or ""
    except Exception:
        av = ""
    return {"id": u.id, "name": (getattr(u, "full_name", "") or "").strip() or "Member", "avatar": av,
            "slug": p.slug if p else None, "headline": p.headline if p else "", "why": why}


def _active(qs):
    qs = qs.filter(is_active=True)
    if any(f.name == "is_blocked" for f in User._meta.get_fields()):
        qs = qs.filter(is_blocked=False)
    return qs


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contacts(request):
    """body: {emails: [...], phones: [...], keep: bool} -> the members among them who can be found."""
    key = "find:checks:%d:%s" % (request.user.pk, timezone.localdate())
    n = cache.get(key, 0)
    if n >= CHECKS_PER_DAY:
        return Response({"detail": "You can check contacts %d times a day. Try again tomorrow." % CHECKS_PER_DAY}, status=429)
    emails = {str(e).strip().lower() for e in (request.data.get("emails") or [])[:MAX_PER_CHECK] if EMAIL.match(str(e).strip())}
    phones = {_digits(p) for p in (request.data.get("phones") or [])[:MAX_PER_CHECK]} - {""}
    if not emails and not phones:
        return Response({"detail": "No email addresses or phone numbers to check."}, status=400)
    cache.set(key, n + 1, 90000)
    kept = None
    if request.data.get("keep"):
        hs = {_h("e", e) for e in emails} | {_h("p", d) for d in phones}
        have = set(ContactHash.objects.filter(user=request.user).values_list("h", flat=True))
        room = MAX_KEPT - len(have)
        ContactHash.objects.bulk_create([ContactHash(user=request.user, h=h) for h in list(hs - have)[:max(room, 0)]], ignore_conflicts=True)
        kept = ContactHash.objects.filter(user=request.user).count()
    off_email = set(FindSetting.objects.filter(by_email=False).values_list("user_id", flat=True))
    off_phone = set(FindSetting.objects.filter(by_phone=False).values_list("user_id", flat=True))
    ids = set()
    if emails:
        from django.db.models.functions import Lower
        ids |= set(User.objects.annotate(_le=Lower("email")).filter(_le__in=list(emails), is_active=True).values_list("id", flat=True)) - off_email
    if phones:
        pm = _phone_map()
        ids |= {pm[d] for d in phones if d in pm} - off_phone
    ids.discard(request.user.id)
    users = _active(User.objects.filter(id__in=ids))
    found = [_card(u) for u in users[:MAX_PER_CHECK]]
    if kept is not None:   # already on the site: no need to say "joined" later
        JoinTold.objects.bulk_create([JoinTold(owner=request.user, joined=u) for u in users[:MAX_PER_CHECK]], ignore_conflicts=True)
    out = {"found": sorted(found, key=lambda x: x["name"].lower()), "checked": len(emails) + len(phones), "checks_left": CHECKS_PER_DAY - n - 1}
    if kept is not None:
        out["kept"] = kept
    return Response(out)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def find_settings(request):
    s, _ = FindSetting.objects.get_or_create(user=request.user)
    if request.method == "POST":
        for f in ("by_email", "by_phone"):
            if f in request.data:
                setattr(s, f, str(request.data.get(f)).lower() in ("true", "1"))
        s.save()
    return Response({"by_email": s.by_email, "by_phone": s.by_phone, "kept": ContactHash.objects.filter(user=request.user).count()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def forget(request):
    n, _ = ContactHash.objects.filter(user=request.user).delete()
    return Response({"deleted": n, "kept": 0})


def on_user_saved(sender, instance, created=False, **kw):
    """When someone joins (or adds a phone number), tell the members who kept them in their contacts."""
    u = instance
    try:
        if not u.is_active or getattr(u, "is_blocked", False):
            return
        s = FindSetting.objects.filter(user=u).first()
        hs = []
        if u.email and (not s or s.by_email):
            hs.append(_h("e", u.email.strip().lower()))
        ph = ""
        for f in ("phone", "phone_number", "mobile"):
            ph = ph or _digits(getattr(u, f, ""))
        if ph and (not s or s.by_phone):
            hs.append(_h("p", ph))
        if not hs:
            return
        owners = set(ContactHash.objects.filter(h__in=hs).exclude(user=u).values_list("user_id", flat=True)[:500])
        if not owners:
            return
        owners -= set(JoinTold.objects.filter(joined=u, owner_id__in=owners).values_list("owner_id", flat=True))
        if not owners:
            return
        JoinTold.objects.bulk_create([JoinTold(owner_id=o, joined=u) for o in owners], ignore_conflicts=True)
        cache.delete("find:phones")
        name = (getattr(u, "full_name", "") or "").strip() or "Someone"
        from notifications.views import notify
        for o in User.objects.filter(id__in=owners, is_active=True):
            notify(o, "connect", "\U0001F4C7 %s from your contacts is now on XpertCreation. Say hello and connect!" % name, "/people#pymk")
    except Exception:
        pass


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def suggest(request):
    """People you may know: kept contacts, friends of friends, same city, same company. Up to 12."""
    me = request.user
    ck = "find:pymk:%d" % me.pk
    hit = cache.get(ck)
    if hit is not None and not request.GET.get("fresh"):
        return Response({"people": hit})
    try:
        from network.models import Connection, Experience, ProProfile
    except Exception:
        return Response({"people": []})
    rel = Connection.objects.filter(Q(from_user=me) | Q(to_user=me)).exclude(state=Connection.DECLINED)
    skip = {me.pk}
    friends = set()
    for a, b, st in rel.values_list("from_user_id", "to_user_id", "state"):
        other = b if a == me.pk else a
        skip.add(other)
        if st == Connection.ACCEPTED:
            friends.add(other)
    score, why = {}, {}

    def add(uid, pts, reason):
        if uid in skip:
            return
        score[uid] = score.get(uid, 0) + pts
        why.setdefault(uid, reason)

    # 1. kept contacts who are members
    hs = set(ContactHash.objects.filter(user=me).values_list("h", flat=True)[:MAX_KEPT])
    if hs:
        off_e = set(FindSetting.objects.filter(by_email=False).values_list("user_id", flat=True))
        off_p = set(FindSetting.objects.filter(by_phone=False).values_list("user_id", flat=True))
        for uid, em in _active(User.objects.exclude(email="")).values_list("id", "email").iterator():
            if uid not in off_e and _h("e", em.strip().lower()) in hs:
                add(uid, 100, "In your contacts")
        for d, uid in _phone_map().items():
            if uid not in off_p and _h("p", d) in hs:
                add(uid, 100, "In your contacts")
    # 2. friends of friends
    if friends:
        mutual = {}
        fof = Connection.objects.filter(state=Connection.ACCEPTED).filter(Q(from_user_id__in=friends) | Q(to_user_id__in=friends))
        for a, b in fof.values_list("from_user_id", "to_user_id")[:5000]:
            for x, y in ((a, b), (b, a)):
                if x in friends:
                    mutual[y] = mutual.get(y, 0) + 1
        for uid, n in mutual.items():
            add(uid, 20 * min(n, 5), "%d mutual connection%s" % (n, "" if n == 1 else "s"))
    mp = ProProfile.objects.filter(user=me).first()
    # 3. same company
    if mp:
        cos = [c for c in Experience.objects.filter(profile=mp).values_list("company", flat=True) if c and len(c) > 2][:5]
        for c in cos:
            for uid in Experience.objects.filter(company__iexact=c).exclude(profile=mp).values_list("profile__user_id", flat=True)[:30]:
                add(uid, 15, "Also at %s" % c)
    # 4. same city
    if mp and mp.city:
        for uid in ProProfile.objects.filter(city__iexact=mp.city).exclude(user=me).exclude(headline="").order_by("-updated_at").values_list("user_id", flat=True)[:30]:
            add(uid, 5, "Lives in %s" % mp.city)
    if not score:
        cache.set(ck, [], 600)
        return Response({"people": []})
    visible = set(ProProfile.objects.filter(user_id__in=list(score)).exclude(visibility=ProProfile.HIDDEN).values_list("user_id", flat=True))
    order = sorted([u for u in score if u in visible], key=lambda u: -score[u])[:12]
    users = {u.pk: u for u in _active(User.objects.filter(pk__in=order))}
    out = [_card(users[u], why[u]) for u in order if u in users]
    cache.set(ck, out, 600)
    return Response({"people": out})
