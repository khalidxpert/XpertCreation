"""/api/meetup/ - Meetup groups (ported from PenFlow, without Pi payments).

Groups by city and topic. Only ID-verified members (approved KYC) can start a group or schedule a meetup,
because people meet strangers in person. Members join groups and get a bell when a new meetup is posted.
Meetups have seats, a waitlist that moves up by itself, an optional map pin, reminders a day before and reviews.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CATEGORIES, MeetGroup, MeetMember, Meetup, MeetReview, MeetRsvp

CAT = dict(CATEGORIES)
GROUPS_PER_USER = 5
MEETUPS_PER_DAY = 5


def _err(m, c=400):
    return Response({"detail": m}, status=c)


def _txt(v, n):
    import re
    return re.sub(r"[ \t]+", " ", str(v or "")).strip()[:n]


def _who(u):
    try:
        from xsocial.views3 import _who as w
        return w(u)
    except Exception:
        return {"id": u.pk, "name": getattr(u, "full_name", "") or u.username, "slug": "", "avatar": "", "verified": False}


def _notify(u, text, link):
    try:
        from notifications.views import notify
        notify(u, "social", text[:200], link)
    except Exception:
        pass


def _kyc_ok(u):
    if not (u and u.is_authenticated):
        return False
    if u.is_staff or u.is_superuser:
        return True
    try:
        from companies.models import PersonKyc
        return PersonKyc.objects.filter(user_id=u.pk, status="approved").exists()
    except Exception:
        return False


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _cover(f, uid):
    from xsocial.views3 import _save_cover
    return _save_cover(f, "meetup", uid)


def _media(rel):
    return ("/media/" + rel) if rel else ""


def _dirty(text):
    for mod, fn in (("academy.views", "_looks_dirty"),):
        try:
            m = __import__(mod, fromlist=[fn])
            return bool(getattr(m, fn)(text))
        except Exception:
            pass
    return False


def _member(g, u):
    return bool(u and u.is_authenticated and MeetMember.objects.filter(group=g, user=u).exists())


def _g_out(g, u=None, full=False):
    now = timezone.now()
    d = {"id": g.id, "slug": g.slug, "name": g.name, "category": g.category, "category_label": CAT.get(g.category, "Other"),
         "city": g.city, "cover": _media(g.cover), "members": g.members_count, "organizer": _who(g.organizer),
         "upcoming": g.meetups.filter(is_active=True, cancelled=False, starts_at__gte=now).count()}
    if full:
        d["about"] = g.about
        d["is_member"] = _member(g, u)
        d["is_organizer"] = bool(u and u.is_authenticated and (g.organizer_id == u.pk or _staff(u)))
        d["recent_members"] = [_who(m.user) for m in g.members.select_related("user").order_by("-joined_at")[:12]]
    return d


def _m_out(m, u=None, full=False):
    going = m.going()
    d = {"id": m.id, "slug": m.slug, "title": m.title, "group": {"id": m.group_id, "slug": m.group.slug, "name": m.group.name},
         "category": m.group.category, "cover": _media(m.cover) or _media(m.group.cover), "online": m.is_online, "city": m.city,
         "place": m.place if not m.is_online else "", "starts": m.starts_at.isoformat(), "minutes": m.minutes,
         "seats": m.seats, "going": going, "seats_left": max(0, m.seats - going) if m.seats else None,
         "cancelled": m.cancelled, "past": m.starts_at < timezone.now()}
    if full:
        mine = MeetRsvp.objects.filter(meetup=m, user=u).first() if (u and u.is_authenticated) else None
        d.update({"about": m.about, "lat": m.lat, "lng": m.lng, "organizer": _who(m.organizer),
                  "my_rsvp": mine.status if mine and mine.status != "cancelled" else "",
                  "is_organizer": bool(u and u.is_authenticated and (m.organizer_id == u.pk or _staff(u))),
                  "waitlist": m.rsvps.filter(status="waitlist").count()})
        d["online_link"] = m.online_link if (m.is_online and (d["my_rsvp"] == "going" or d["is_organizer"])) else ""
        if u and u.is_authenticated:
            d["attendees"] = [_who(r.user) for r in m.rsvps.filter(status="going").select_related("user").order_by("created_at")[:60]]
        else:
            d["attendees"] = []
        revs = list(m.reviews.select_related("user").order_by("-created_at")[:20])
        d["reviews"] = [{"by": _who(r.user), "rating": r.rating, "comment": r.comment, "when": r.created_at.isoformat()} for r in revs]
        d["rating"] = round(sum(r.rating for r in revs) / len(revs), 1) if revs else 0
        d["can_review"] = bool(d["past"] and d["my_rsvp"] == "going" and not m.reviews.filter(user=u).exists())
    return d


# ------------------------------------------------------------------ config / mine
@api_view(["GET"])
@permission_classes([AllowAny])
def config(request):
    u = request.user
    return Response({"signed_in": u.is_authenticated, "verified": _kyc_ok(u),
                     "categories": [{"key": k, "label": v} for k, v in CATEGORIES]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mine(request):
    u = request.user; now = timezone.now()
    groups = MeetGroup.objects.filter(members__user=u, is_active=True).select_related("organizer").distinct()
    rs = MeetRsvp.objects.filter(user=u, status__in=["going", "waitlist"], meetup__is_active=True,
                                 meetup__starts_at__gte=now - timedelta(hours=6)).select_related("meetup", "meetup__group").order_by("meetup__starts_at")
    return Response({"groups": [_g_out(g) for g in groups],
                     "meetups": [dict(_m_out(r.meetup), my_rsvp=r.status) for r in rs[:50]]})


# ------------------------------------------------------------------ groups
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def groups(request):
    u = request.user
    if request.method == "GET":
        qs = MeetGroup.objects.filter(is_active=True).select_related("organizer")
        q, city, cat = _txt(request.GET.get("q"), 60), _txt(request.GET.get("city"), 60), request.GET.get("cat", "")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(about__icontains=q))
        if city:
            qs = qs.filter(city__icontains=city)
        if cat in CAT:
            qs = qs.filter(category=cat)
        return Response({"groups": [_g_out(g) for g in qs.order_by("-members_count", "-created_at")[:60]]})
    if not u.is_authenticated:
        return _err("Sign in to start a group.", 401)
    if not _kyc_ok(u):
        return _err("Only members with a verified ID can start a meetup group. Verify your ID first on /get-verified.", 403)
    if MeetGroup.objects.filter(organizer=u, is_active=True).count() >= GROUPS_PER_USER:
        return _err("You can run up to %d groups." % GROUPS_PER_USER)
    d = request.data
    name, about, city = _txt(d.get("name"), 120), str(d.get("about") or "").strip()[:3000], _txt(d.get("city"), 60)
    cat = d.get("category") if d.get("category") in CAT else "other"
    if len(name) < 4:
        return _err("Give the group a name (at least 4 letters).")
    if not city:
        return _err("Which city is the group in?")
    if _dirty(name) or _dirty(about):
        return _err("That wording is not allowed here.")
    cover = ""
    if request.FILES.get("cover"):
        try:
            cover = _cover(request.FILES["cover"], u.pk)
        except ValueError as e:
            return _err(str(e))
    with transaction.atomic():
        g = MeetGroup.objects.create(organizer=u, name=name, about=about, city=city, category=cat, cover=cover, members_count=1)
        MeetMember.objects.create(group=g, user=u, role="organizer")
    return Response({"ok": True, "id": g.id, "slug": g.slug}, status=201)


@api_view(["GET"])
@permission_classes([AllowAny])
def group_detail(request, slug):
    g = MeetGroup.objects.filter(slug=slug, is_active=True).select_related("organizer").first()
    if not g:
        return _err("Group not found.", 404)
    now = timezone.now()
    d = _g_out(g, request.user, full=True)
    ms = g.meetups.filter(is_active=True).select_related("group")
    d["meetups"] = [_m_out(m) for m in ms.filter(starts_at__gte=now - timedelta(hours=6)).order_by("starts_at")[:30]]
    d["past"] = [_m_out(m) for m in ms.filter(starts_at__lt=now - timedelta(hours=6)).order_by("-starts_at")[:12]]
    return Response(d)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_join(request, gid):
    g = MeetGroup.objects.filter(pk=gid, is_active=True).first()
    if not g:
        return _err("Group not found.", 404)
    _, made = MeetMember.objects.get_or_create(group=g, user=request.user)
    if made:
        MeetGroup.objects.filter(pk=g.pk).update(members_count=g.members.count())
        _notify(g.organizer, "%s joined your group %s." % (_who(request.user)["name"], g.name), "/meetups#g/" + g.slug)
    return Response({"ok": True, "members": g.members.count()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_leave(request, gid):
    g = MeetGroup.objects.filter(pk=gid).first()
    if not g:
        return _err("Group not found.", 404)
    if g.organizer_id == request.user.pk:
        return _err("You run this group, so you can't leave it.")
    MeetMember.objects.filter(group=g, user=request.user).delete()
    MeetGroup.objects.filter(pk=g.pk).update(members_count=g.members.count())
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def group_edit(request, gid):
    g = MeetGroup.objects.filter(pk=gid).first()
    if not g or not (g.organizer_id == request.user.pk or _staff(request.user)):
        return _err("Group not found.", 404)
    d = request.data
    if d.get("delete") in (True, "1", "true"):
        g.is_active = False; g.save(update_fields=["is_active"]); return Response({"ok": True, "deleted": True})
    if "name" in d:
        n = _txt(d.get("name"), 120)
        if len(n) >= 4 and not _dirty(n):
            g.name = n
    if "about" in d and not _dirty(str(d.get("about"))):
        g.about = str(d.get("about") or "").strip()[:3000]
    if "city" in d and _txt(d.get("city"), 60):
        g.city = _txt(d.get("city"), 60)
    if d.get("category") in CAT:
        g.category = d.get("category")
    if request.FILES.get("cover"):
        try:
            g.cover = _cover(request.FILES["cover"], request.user.pk)
        except ValueError as e:
            return _err(str(e))
    g.save()
    return Response({"ok": True, "slug": g.slug})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def group_members(request, gid):
    g = MeetGroup.objects.filter(pk=gid, is_active=True).first()
    if not g:
        return _err("Group not found.", 404)
    rows = g.members.select_related("user").order_by("joined_at")[:500]
    return Response({"members": [dict(_who(m.user), role=m.role, joined=m.joined_at.isoformat()) for m in rows]})


# ------------------------------------------------------------------ meetups
@api_view(["GET"])
@permission_classes([AllowAny])
def meetups(request):
    now = timezone.now()
    qs = Meetup.objects.filter(is_active=True, cancelled=False, group__is_active=True, starts_at__gte=now - timedelta(hours=3)).select_related("group")
    q, city, cat = _txt(request.GET.get("q"), 60), _txt(request.GET.get("city"), 60), request.GET.get("cat", "")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(about__icontains=q) | Q(group__name__icontains=q))
    if city:
        qs = qs.filter(Q(city__icontains=city) | Q(is_online=True))
    if cat in CAT:
        qs = qs.filter(group__category=cat)
    return Response({"meetups": [_m_out(m) for m in qs.order_by("starts_at")[:80]]})


@api_view(["GET"])
@permission_classes([AllowAny])
def meetup_detail(request, slug):
    m = Meetup.objects.filter(slug=slug, is_active=True, group__is_active=True).select_related("group", "organizer").first()
    if not m:
        return _err("Meetup not found.", 404)
    Meetup.objects.filter(pk=m.pk).update(views=m.views + 1)
    return Response(_m_out(m, request.user, full=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def meetup_create(request, gid):
    u = request.user
    g = MeetGroup.objects.filter(pk=gid, is_active=True).first()
    if not g or not (g.organizer_id == u.pk or _staff(u)):
        return _err("Only the group organiser can schedule meetups.", 403)
    if not _kyc_ok(u):
        return _err("Verify your ID first on /get-verified to organise meetups.", 403)
    if Meetup.objects.filter(organizer=u, created_at__gte=timezone.now() - timedelta(days=1)).count() >= MEETUPS_PER_DAY:
        return _err("You can schedule %d meetups a day." % MEETUPS_PER_DAY)
    d = request.data
    title, about = _txt(d.get("title"), 140), str(d.get("about") or "").strip()[:4000]
    if len(title) < 4:
        return _err("Give the meetup a title.")
    if _dirty(title) or _dirty(about):
        return _err("That wording is not allowed here.")
    st = parse_datetime(str(d.get("starts") or ""))
    if not st:
        return _err("Choose a date and time.")
    if timezone.is_naive(st):
        st = timezone.make_aware(st)
    if st < timezone.now() + timedelta(minutes=30) or st > timezone.now() + timedelta(days=366):
        return _err("The date must be at least 30 minutes from now and within a year.")
    online = str(d.get("online")).lower() in ("1", "true", "yes")
    place, city, link = _txt(d.get("place"), 200), _txt(d.get("city"), 60) or g.city, str(d.get("online_link") or "").strip()[:300]
    if online and not link.startswith(("https://", "http://")):
        return _err("Add the online meeting link (Zoom, Google Meet…).")
    if not online and not place:
        return _err("Where is it? Add the venue or address.")
    def num(k, lo, hi, dflt):
        try:
            v = float(d.get(k))
            return v if lo <= v <= hi else dflt
        except (TypeError, ValueError):
            return dflt
    lat, lng = num("lat", -90, 90, None), num("lng", -180, 180, None)
    seats = int(num("seats", 0, 5000, 50))
    minutes = int(num("minutes", 15, 24 * 60, 120))
    cover = ""
    if request.FILES.get("cover"):
        try:
            cover = _cover(request.FILES["cover"], u.pk)
        except ValueError as e:
            return _err(str(e))
    m = Meetup.objects.create(group=g, organizer=u, title=title, about=about, cover=cover, is_online=online, place="" if online else place,
                              city=city, lat=None if online else lat, lng=None if online else lng, online_link=link if online else "",
                              starts_at=st, minutes=minutes, seats=seats)
    MeetRsvp.objects.get_or_create(meetup=m, user=u, defaults={"status": "going"})
    for mem in g.members.exclude(user=u).select_related("user")[:2000]:
        _notify(mem.user, "New meetup in %s: %s" % (g.name, title), "/meetups#m/" + m.slug)
    return Response({"ok": True, "id": m.id, "slug": m.slug}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rsvp(request, mid):
    u = request.user
    with transaction.atomic():
        m = Meetup.objects.select_for_update().filter(pk=mid, is_active=True).select_related("group").first()
        if not m or m.cancelled:
            return _err("This meetup is not open.", 404)
        if m.starts_at < timezone.now():
            return _err("This meetup has already started.")
        want = str(request.data.get("going", True)).lower() not in ("0", "false", "no")
        r = MeetRsvp.objects.filter(meetup=m, user=u).first()
        if want:
            if r and r.status in ("going", "waitlist"):
                return Response({"ok": True, "status": r.status})
            full = bool(m.seats) and m.going() >= m.seats
            st = "waitlist" if full else "going"
            if r:
                r.status = st; r.save(update_fields=["status", "updated_at"])
            else:
                MeetRsvp.objects.create(meetup=m, user=u, status=st)
            MeetMember.objects.get_or_create(group=m.group, user=u)
            MeetGroup.objects.filter(pk=m.group_id).update(members_count=m.group.members.count())
            if st == "going" and m.organizer_id != u.pk:
                _notify(m.organizer, "%s is going to %s." % (_who(u)["name"], m.title), "/meetups#m/" + m.slug)
            return Response({"ok": True, "status": st})
        if not r or r.status == "cancelled":
            return Response({"ok": True, "status": ""})
        was = r.status
        r.status = "cancelled"; r.save(update_fields=["status", "updated_at"])
        if was == "going":
            nxt = MeetRsvp.objects.filter(meetup=m, status="waitlist").order_by("created_at").first()
            if nxt and (not m.seats or m.going() < m.seats):
                nxt.status = "going"; nxt.save(update_fields=["status", "updated_at"])
                _notify(nxt.user, "A seat opened up - you're now going to %s." % m.title, "/meetups#m/" + m.slug)
    return Response({"ok": True, "status": ""})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def meetup_cancel(request, mid):
    m = Meetup.objects.filter(pk=mid, is_active=True).first()
    if not m or not (m.organizer_id == request.user.pk or _staff(request.user)):
        return _err("Meetup not found.", 404)
    if not m.cancelled:
        m.cancelled = True; m.save(update_fields=["cancelled"])
        for r in m.rsvps.filter(status__in=["going", "waitlist"]).exclude(user=m.organizer).select_related("user"):
            _notify(r.user, "Cancelled: %s (%s)." % (m.title, timezone.localtime(m.starts_at).strftime("%d %b, %I:%M %p")), "/meetups#m/" + m.slug)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review(request, mid):
    u = request.user
    m = Meetup.objects.filter(pk=mid, is_active=True).first()
    if not m or m.starts_at > timezone.now():
        return _err("You can review a meetup after it has taken place.")
    if not MeetRsvp.objects.filter(meetup=m, user=u, status="going").exists():
        return _err("Only people who went can review it.")
    try:
        rating = max(1, min(5, int(request.data.get("rating", 5))))
    except (TypeError, ValueError):
        rating = 5
    comment = _txt(request.data.get("comment"), 500)
    if _dirty(comment):
        return _err("That wording is not allowed here.")
    MeetReview.objects.update_or_create(meetup=m, user=u, defaults={"rating": rating, "comment": comment})
    return Response({"ok": True})


# ------------------------------------------------------------------ reminders (cron)
def tick():
    """A day before: remind everyone who is going. Safe to run every 15 minutes."""
    now = timezone.now(); n = 0
    for m in Meetup.objects.filter(is_active=True, cancelled=False, reminded_day=False, starts_at__gt=now, starts_at__lte=now + timedelta(hours=24)):
        when = timezone.localtime(m.starts_at).strftime("%a %d %b, %I:%M %p")
        for r in m.rsvps.filter(status="going").select_related("user"):
            _notify(r.user, "Reminder: %s is tomorrow (%s)%s." % (m.title, when, "" if m.is_online else " at " + (m.place or m.city)), "/meetups#m/" + m.slug)
            n += 1
        Meetup.objects.filter(pk=m.pk).update(reminded_day=True)
    return n
