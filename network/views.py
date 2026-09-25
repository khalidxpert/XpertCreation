"""Professional network: profiles, skills, endorsements, experience, education,
connections (chat opens only once both people agree), follows, and blue tick requests.

Visibility: public (anyone, and Google), members (signed-in people), hidden (owner only).
Only verified, active, unblocked members appear to anyone else.
"""
import re
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from accounts.views import avatar_url
from notifications.views import notify, notify_admins, open_thread

from .models import (Connection, Education, Endorsement, Experience, Follow, ProfileReport,
                     ProProfile, Skill, VerificationRequest)

YES = (True, "true", "True", "1", 1, "on", "yes")
TICK_FOLLOWERS = 1000
DAILY_REQUESTS = 30
MAX_PENDING = 200
ASK_AGAIN_DAYS = 30


class _Throttle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ident = request.user.pk if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class EditThrottle(_Throttle):
    scope = "net_edit"


class EndorseThrottle(_Throttle):
    scope = "net_endorse"


class ReportThrottle(_Throttle):
    scope = "net_report"


class BrowseThrottle(_Throttle):
    scope = "net_browse"


class ConnectThrottle(_Throttle):
    scope = "net_connect"


class FollowThrottle(_Throttle):
    scope = "net_follow"


def _err(msg, code=400):
    return Response({"detail": msg}, status=code)


def _txt(v, n):
    return re.sub(r"[ \t]+", " ", str(v or "")).strip()[:n]


def _int(v, lo, hi):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def _name(u):
    return (u.full_name or "").strip() or "Member"


def _av(u):
    try:
        return avatar_url(u.avatar) if u.avatar else ""
    except Exception:
        return ""


def _is_mod(v):
    return v.is_authenticated and (v.is_staff or getattr(v, "is_moderator", False))


def _viewable(p, viewer):
    u = p.user
    if viewer.is_authenticated and viewer.pk == u.pk:
        return True
    if not u.is_active or u.is_blocked:
        return False
    if _is_mod(viewer):
        return True
    if not u.is_email_verified:
        return False
    if p.visibility == ProProfile.PUBLIC:
        return True
    if p.visibility == ProProfile.MEMBERS:
        return viewer.is_authenticated
    return False


def _ticked(p):
    """Blue tick: approved by hand, or automatic for staff, admins and moderators."""
    u = p.user
    return bool(p.verified or u.is_staff or u.is_superuser or getattr(u, "is_moderator", False))


def _unique_slug(name):
    base = slugify(name)[:40] or "member"
    slug, n = base, 2
    while ProProfile.objects.filter(slug=slug).exists():
        slug = "%s-%d" % (base, n)
        n += 1
    return slug


def _get_or_make(user):
    p = ProProfile.objects.filter(user=user).first()
    if p:
        return p
    for _ in range(3):
        try:
            return ProProfile.objects.create(user=user, slug=_unique_slug(_name(user)))
        except IntegrityError:
            p = ProProfile.objects.filter(user=user).first()
            if p:
                return p
    raise IntegrityError("could not create profile")


def _link_of(user):
    s = ProProfile.objects.filter(user=user).values_list("slug", flat=True).first()
    return "/in/%s" % s if s else "/people"


def _followers(user):
    return Follow.objects.filter(following=user, follower__is_active=True, follower__is_blocked=False,
                                 follower__is_email_verified=True).count()


def _between(a, b):
    return Connection.objects.filter(Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a)).first()


def _relation(viewer, u):
    if not viewer.is_authenticated or viewer.pk == u.pk:
        return None
    c = _between(viewer, u)
    state = "none"
    if c:
        if c.state == Connection.ACCEPTED:
            state = "connected"
        elif c.state == Connection.PENDING:
            state = "outgoing" if c.from_user_id == viewer.pk else "incoming"
        elif c.state == Connection.DECLINED and c.from_user_id == viewer.pk:
            state = "declined"
    return {"connection": state,
            "request_id": c.pk if (c and state == "incoming") else None,
            "following": Follow.objects.filter(follower=viewer, following=u).exists()}


def _exp(x):
    return {"id": x.pk, "title": x.title, "company": x.company, "city": x.city,
            "start_month": x.start_month, "start_year": x.start_year,
            "end_month": x.end_month, "end_year": x.end_year,
            "current": x.end_year is None, "description": x.description}


def _edu(x):
    return {"id": x.pk, "school": x.school, "degree": x.degree, "field": x.field,
            "start_year": x.start_year, "end_year": x.end_year}


def _full(p, viewer):
    u = p.user
    skills = list(p.skills.annotate(n=Count("endorsements")).order_by("-n", "order", "id"))
    mine = set()
    if viewer.is_authenticated:
        mine = set(Endorsement.objects.filter(endorser=viewer, skill__profile=p)
                   .values_list("skill_id", flat=True))
    by = {}
    for e in (Endorsement.objects.filter(skill__profile=p).select_related("endorser")
              .order_by("-created_at")[:300]):
        lst = by.setdefault(e.skill_id, [])
        if len(lst) < 5:
            lst.append(_name(e.endorser))
    exp = sorted(p.experience.all(),
                 key=lambda x: (x.end_year is not None, -(x.start_year or 0), -(x.start_month or 0)))
    is_me = viewer.is_authenticated and viewer.pk == u.pk
    followers = _followers(u)
    out = {
        "slug": p.slug, "user_id": u.pk, "name": _name(u), "avatar": u.avatar or "", "avatar_url": _av(u),
        "country": (p.country or u.signup_country or "").upper(),
        "headline": p.headline, "about": p.about, "city": p.city, "state": p.state,
        "socials": p.socials or {},
        "open_to_work": p.open_to_work, "open_to": p.open_to,
        "visibility": p.visibility if is_me else None,
        "website": p.website, "linkedin": p.linkedin, "github": p.github,
        "verified": _ticked(p),
        "followers": followers,
        "following": Follow.objects.filter(follower=u).count(),
        "connections": Connection.objects.filter(Q(from_user=u) | Q(to_user=u),
                                                 state=Connection.ACCEPTED).count(),
        "relation": _relation(viewer, u),
        "skills": [{"id": s.pk, "name": s.name, "count": s.n, "mine": s.pk in mine,
                    "by": by.get(s.pk, [])} for s in skills],
        "experience": [_exp(x) for x in exp],
        "education": [_edu(x) for x in p.education.all()],
        "is_me": is_me,
        "can_endorse": (viewer.is_authenticated and not is_me
                        and bool(getattr(viewer, "is_email_verified", False))),
        "member_since": u.date_joined.strftime("%b %Y"),
    }
    if is_me:
        pending = VerificationRequest.objects.filter(profile=p, state=VerificationRequest.PENDING).exists()
        out["tick"] = {"needed": TICK_FOLLOWERS, "pending": pending,
                       "can_apply": (not _ticked(p)) and (not pending) and followers >= TICK_FOLLOWERS}
        out["requests"] = Connection.objects.filter(to_user=u, state=Connection.PENDING).count()
    return out


def _card(p):
    u = p.user
    return {"slug": p.slug, "name": _name(u), "avatar": u.avatar or "", "avatar_url": _av(u),
            "country": (p.country or u.signup_country or "").upper(), "headline": p.headline,
            "city": p.city, "open_to_work": p.open_to_work, "verified": _ticked(p),
            "skills": [s.name for s in p.skills.all()][:3],
            "endorsements": getattr(p, "en", 0)}


def _clean_url(v, label):
    v = str(v or "").strip()[:200]
    if not v:
        return ""
    if not v.startswith(("http://", "https://")):
        v = "https://" + v
    try:
        URLValidator(schemes=["http", "https"])(v)
    except ValidationError:
        raise ValueError("That %s link does not look right." % label)
    return v


def _find(slug, viewer):
    p = ProProfile.objects.select_related("user").filter(slug=str(slug)[:60]).first()
    if not p or not _viewable(p, viewer):
        return None
    return p


# ---------------------------------------------------------------- own profile

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def me(request):
    p = _get_or_make(request.user)
    if request.method == "POST":
        d = request.data
        for field, n in (("headline", 120), ("city", 60), ("open_to", 120)):
            if field in d:
                setattr(p, field, _txt(d.get(field), n))
        if "about" in d:
            p.about = str(d.get("about") or "").replace("\r\n", "\n").strip()[:2000]
        if "open_to_work" in d:
            p.open_to_work = d.get("open_to_work") in YES
        if "visibility" in d:
            if d.get("visibility") not in dict(ProProfile.VISIBILITY):
                return _err("Pick public, members or hidden.")
            p.visibility = d.get("visibility")
        if "country" in d:
            cc = str(d.get("country") or "").strip().upper()[:2]
            p.country = cc if (len(cc) == 2 and cc.isalpha()) else ""
        if "state" in d:
            p.state = _txt(d.get("state"), 100)
        if isinstance(d.get("socials"), dict):
            clean = {}
            for k, val in list(d.get("socials").items())[:60]:
                if str(k) in SOCIAL_KEYS:
                    h = re.sub(r"[^\w.\-+@/:~]", "", str(val or "").strip())[:100].lstrip("@")
                    if h:
                        clean[str(k)] = h
            p.socials = clean
        for field, label in (("website", "website"), ("linkedin", "LinkedIn"), ("github", "GitHub")):
            if field in d:
                try:
                    setattr(p, field, _clean_url(d.get(field), label))
                except ValueError as e:
                    return _err(str(e))
        p.save()
    return Response(_full(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def skill_add(request):
    p = _get_or_make(request.user)
    name = _txt(request.data.get("name"), 40)
    if len(name) < 2:
        return _err("Type a skill, at least two letters.")
    if p.skills.count() >= 30:
        return _err("Thirty skills is the limit. Remove one to add another.")
    if p.skills.filter(name__iexact=name).exists():
        return _err("That skill is already on your profile.")
    try:
        Skill.objects.create(profile=p, name=name, order=p.skills.count())
    except IntegrityError:
        return _err("That skill is already on your profile.")
    return Response(_full(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def skill_delete(request, pk):
    p = _get_or_make(request.user)
    p.skills.filter(pk=pk).delete()
    return Response(_full(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def exp_save(request):
    p = _get_or_make(request.user)
    d = request.data
    yr = timezone.now().year
    title = _txt(d.get("title"), 100)
    if not title:
        return _err("Add a job title.")
    sy = _int(d.get("start_year"), 1950, yr + 1)
    if sy is None:
        return _err("Add the year you started.")
    sm = _int(d.get("start_month"), 1, 12)
    current = d.get("current") in YES
    ey = None if current else _int(d.get("end_year"), 1950, yr + 1)
    em = None if current else _int(d.get("end_month"), 1, 12)
    if not current and ey is None:
        return _err("Add the year you left, or tick that you still work here.")
    if ey is not None and (ey, em or 12) < (sy, sm or 1):
        return _err("The end date is before the start date.")
    pk = _int(d.get("id"), 1, 2 ** 62)
    if pk:
        x = p.experience.filter(pk=pk).first()
        if not x:
            return _err("That entry was not found.", 404)
    else:
        if p.experience.count() >= 20:
            return _err("Twenty jobs is the limit.")
        x = Experience(profile=p)
    x.title, x.company, x.city = title, _txt(d.get("company"), 100), _txt(d.get("city"), 60)
    x.start_year, x.start_month, x.end_year, x.end_month = sy, sm, ey, em
    x.description = str(d.get("description") or "").replace("\r\n", "\n").strip()[:1000]
    x.save()
    return Response(_full(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def exp_delete(request, pk):
    p = _get_or_make(request.user)
    p.experience.filter(pk=pk).delete()
    return Response(_full(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def edu_save(request):
    p = _get_or_make(request.user)
    d = request.data
    yr = timezone.now().year
    school = _txt(d.get("school"), 120)
    if not school:
        return _err("Add the name of the school, college or university.")
    sy = _int(d.get("start_year"), 1950, yr + 10)
    ey = _int(d.get("end_year"), 1950, yr + 10)
    if sy and ey and ey < sy:
        return _err("The end year is before the start year.")
    pk = _int(d.get("id"), 1, 2 ** 62)
    if pk:
        x = p.education.filter(pk=pk).first()
        if not x:
            return _err("That entry was not found.", 404)
    else:
        if p.education.count() >= 10:
            return _err("Ten entries is the limit.")
        x = Education(profile=p)
    x.school, x.degree, x.field = school, _txt(d.get("degree"), 100), _txt(d.get("field"), 100)
    x.start_year, x.end_year = sy, ey
    x.save()
    return Response(_full(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def edu_delete(request, pk):
    p = _get_or_make(request.user)
    p.education.filter(pk=pk).delete()
    return Response(_full(p, request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def requests_list(request):
    rows = list(Connection.objects.filter(to_user=request.user, state=Connection.PENDING)
                .select_related("from_user").order_by("-created_at")[:100])
    profs = {pp.user_id: pp for pp in ProProfile.objects.filter(user_id__in=[r.from_user_id for r in rows])}
    out = []
    for r in rows:
        u = r.from_user
        if not u.is_active or u.is_blocked:
            continue
        pp = profs.get(u.pk)
        out.append({"id": r.pk, "name": _name(u), "avatar_url": _av(u),
                    "slug": pp.slug if pp else None, "headline": pp.headline if pp else "",
                    "when": r.created_at.strftime("%d %b %Y")})
    return Response({"requests": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ConnectThrottle])
def request_respond(request, pk, action):
    if action not in ("accept", "decline"):
        return _err("Accept or decline.", 404)
    c = (Connection.objects.filter(pk=pk, to_user=request.user, state=Connection.PENDING)
         .select_related("from_user").first())
    if not c:
        return _err("That request is no longer waiting.", 404)
    c.state = Connection.ACCEPTED if action == "accept" else Connection.DECLINED
    c.responded_at = timezone.now()
    c.save(update_fields=["state", "responded_at"])
    if c.state == Connection.ACCEPTED:
        notify(c.from_user, "connect", "%s accepted your connection request" % _name(request.user),
               _link_of(request.user))
    return Response({"ok": True, "state": c.state})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def tick_apply(request):
    p = _get_or_make(request.user)
    if _ticked(p):
        return _err("You already have the blue tick.")
    if VerificationRequest.objects.filter(profile=p, state=VerificationRequest.PENDING).exists():
        return _err("Your request is already waiting for review.")
    if not p.headline:
        return _err("Fill in your headline before applying.")
    followers = _followers(request.user)
    if followers < TICK_FOLLOWERS:
        return _err("You need %d followers to apply. You have %d." % (TICK_FOLLOWERS, followers))
    VerificationRequest.objects.create(profile=p, followers_at_request=followers)
    notify_admins("tick", "Blue tick request: %s (%d followers)" % (_name(request.user), followers),
                  "/in/%s" % p.slug)
    return Response(_full(p, request.user))


# ---------------------------------------------------------------- everyone else

@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def people(request):
    v = request.user
    qs = (ProProfile.objects
          .filter(user__is_active=True, user__is_blocked=False, user__is_email_verified=True)
          .exclude(visibility=ProProfile.HIDDEN).exclude(headline=""))
    if not v.is_authenticated:
        qs = qs.filter(visibility=ProProfile.PUBLIC)
    q = _txt(request.GET.get("q"), 60)
    if q:
        qs = qs.filter(Q(user__full_name__icontains=q) | Q(headline__icontains=q)
                       | Q(skills__name__icontains=q) | Q(city__icontains=q))
    ctry = str(request.GET.get("country") or "").upper()[:2]
    if len(ctry) == 2 and ctry.isalpha():
        qs = qs.filter(Q(country=ctry) | Q(country="", user__signup_country=ctry))
    city = _txt(request.GET.get("city"), 60)
    if city:
        qs = qs.filter(city__icontains=city)
    skill = _txt(request.GET.get("skill"), 40)
    if skill:
        qs = qs.filter(skills__name__iexact=skill)
    if request.GET.get("open") in YES:
        qs = qs.filter(open_to_work=True)
    qs = qs.annotate(en=Count("skills__endorsements", distinct=True)).distinct()
    total = qs.count()
    size = 24
    page = _int(request.GET.get("page"), 1, 1000) or 1
    rows = list(qs.select_related("user").prefetch_related("skills")
                .order_by("-verified", "-en", "-updated_at")[(page - 1) * size: page * size])
    return Response({"total": total, "page": page, "pages": (total + size - 1) // size,
                     "people": [_card(p) for p in rows]})


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def profile(request, slug):
    p = _find(slug, request.user)
    if not p:
        return _err("This profile is private or does not exist.", 404)
    return Response(_full(p, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([EndorseThrottle])
def endorse(request, slug):
    me_ = request.user
    p = _find(slug, me_)
    if not p:
        return _err("This profile is private or does not exist.", 404)
    if p.user_id == me_.pk:
        return _err("You cannot endorse your own skills.")
    if not getattr(me_, "is_email_verified", False):
        return _err("Verify your email before endorsing anyone.", 403)
    skill = p.skills.filter(pk=_int(request.data.get("skill_id"), 1, 2 ** 62) or 0).first()
    if not skill:
        return _err("That skill was not found.", 404)
    old = Endorsement.objects.filter(skill=skill, endorser=me_).first()
    if old:
        old.delete()
        endorsed = False
    else:
        try:
            Endorsement.objects.create(skill=skill, endorser=me_)
        except IntegrityError:
            pass
        endorsed = True
        notify(p.user, "endorse", "%s endorsed you for %s" % (_name(me_), skill.name),
               "/in/%s" % p.slug)
    return Response({"endorsed": endorsed, "count": skill.endorsements.count()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ReportThrottle])
def report(request, slug):
    p = _find(slug, request.user)
    if not p:
        return _err("This profile is private or does not exist.", 404)
    if p.user_id == request.user.pk:
        return _err("You cannot report your own profile.")
    reason = request.data.get("reason")
    if reason not in dict(ProfileReport.REASONS):
        return _err("Pick a reason.")
    ProfileReport.objects.update_or_create(
        profile=p, reporter=request.user, handled=False,
        defaults={"reason": reason, "note": _txt(request.data.get("note"), 500)})
    notify_admins("report", "Profile reported (%s): %s" % (reason, _name(p.user)), "/in/%s" % p.slug)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ConnectThrottle])
def connect(request, slug):
    me_ = request.user
    p = _find(slug, me_)
    if not p:
        return _err("This profile is private or does not exist.", 404)
    other = p.user
    if other.pk == me_.pk:
        return _err("That is your own profile.")
    if not getattr(me_, "is_email_verified", False):
        return _err("Verify your email before connecting with anyone.", 403)
    now = timezone.now()
    c = _between(me_, other)
    if c and c.state == Connection.ACCEPTED:
        return Response({"connection": "connected"})
    if c and c.state == Connection.PENDING:
        if c.to_user_id == me_.pk:           # they had already asked - this accepts it
            c.state, c.responded_at = Connection.ACCEPTED, now
            c.save(update_fields=["state", "responded_at"])
            notify(other, "connect", "%s accepted your connection request" % _name(me_), _link_of(me_))
            return Response({"connection": "connected"})
        return Response({"connection": "outgoing"})
    if c and c.state == Connection.DECLINED and c.from_user_id == me_.pk and c.responded_at \
            and now - c.responded_at < timedelta(days=ASK_AGAIN_DAYS):
        return _err("You can ask again %d days after a request is declined." % ASK_AGAIN_DAYS)
    if Connection.objects.filter(from_user=me_, created_at__gte=now - timedelta(days=1)).count() >= DAILY_REQUESTS:
        return _err("%d requests a day is the limit. Try again tomorrow." % DAILY_REQUESTS)
    if Connection.objects.filter(from_user=me_, state=Connection.PENDING).count() >= MAX_PENDING:
        return _err("You have too many requests waiting. Withdraw some first.")
    if c:                                    # an old declined one - ask again on the same row
        c.from_user, c.to_user = me_, other
        c.state, c.created_at, c.responded_at = Connection.PENDING, now, None
        c.save()
    else:
        try:
            Connection.objects.create(from_user=me_, to_user=other)
        except IntegrityError:
            return Response({"connection": "outgoing"})
    notify(other, "connect", "%s wants to connect with you" % _name(me_), "/me/profile#requests")
    return Response({"connection": "outgoing"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ConnectThrottle])
def disconnect(request, slug):
    me_ = request.user
    p = _find(slug, me_)
    if not p:
        return _err("This profile is private or does not exist.", 404)
    c = _between(me_, p.user)
    if c and (c.state == Connection.ACCEPTED
              or (c.state == Connection.PENDING and c.from_user_id == me_.pk)):
        c.delete()
    return Response({"connection": "none"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ConnectThrottle])
def message(request, slug):
    me_ = request.user
    p = _find(slug, me_)
    if not p:
        return _err("This profile is private or does not exist.", 404)
    c = _between(me_, p.user)
    if not c or c.state != Connection.ACCEPTED:
        return _err("You can message people once you are connected.", 403)
    t = open_thread("connect", c.pk, me_, p.user)
    return Response({"id": t.id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([FollowThrottle])
def follow(request, slug):
    me_ = request.user
    p = _find(slug, me_)
    if not p:
        return _err("This profile is private or does not exist.", 404)
    if p.user_id == me_.pk:
        return _err("You cannot follow yourself.")
    old = Follow.objects.filter(follower=me_, following=p.user).first()
    if old:
        old.delete()
        following = False
    else:
        try:
            Follow.objects.create(follower=me_, following=p.user)
        except IntegrityError:
            pass
        following = True
        notify(p.user, "follow", "%s started following you" % _name(me_), _link_of(me_))
    return Response({"following": following, "followers": _followers(p.user)})


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([BrowseThrottle])
def cities(request):
    """Cities members have put on their profiles, most used first - fills the city box."""
    from django.core.cache import cache
    hit = cache.get("net:cities")
    if hit is None:
        rows = (ProProfile.objects.exclude(city="")
                .filter(user__is_active=True, user__is_blocked=False)
                .values("city").annotate(n=Count("id")).order_by("-n")[:300])
        merged = {}
        for r in rows:
            name = " ".join(w[:1].upper() + w[1:] for w in r["city"].split())
            merged[name] = merged.get(name, 0) + r["n"]
        hit = [{"city": c, "n": n} for c, n in sorted(merged.items(), key=lambda x: -x[1])]
        cache.set("net:cities", hit, 600)
    return Response({"cities": hit})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([EditThrottle])
def my_people(request, which):
    """The signed-in member's connections, followers, or the people they follow."""
    me_ = request.user
    if which == "connections":
        rows = (Connection.objects.filter(Q(from_user=me_) | Q(to_user=me_), state=Connection.ACCEPTED)
                .select_related("from_user", "to_user").order_by("-responded_at"))
        users = [c.to_user if c.from_user_id == me_.pk else c.from_user for c in rows]
    elif which == "followers":
        users = [f.follower for f in Follow.objects.filter(following=me_).select_related("follower").order_by("-created_at")]
    elif which == "following":
        users = [f.following for f in Follow.objects.filter(follower=me_).select_related("following").order_by("-created_at")]
    else:
        return _err("Unknown list.", 404)
    users = [u for u in users if u.is_active and not u.is_blocked][:500]
    out = []
    for u in users:
        # Connections always get a profile, so the Message button has somewhere to go.
        p = _get_or_make(u) if which == "connections" else ProProfile.objects.filter(user=u).first()
        out.append({"user_id": u.pk, "name": _name(u), "avatar_url": _av(u),
                    "slug": p.slug if p else None, "headline": p.headline if p else "",
                    "verified": _ticked(p) if p else False})
    return Response({"which": which, "people": out})


SOCIAL_KEYS = {'pinterest', 'skype', 'stackoverflow', 'reddit', 'facebook', 'twitch', 'linkedin', 'vk', 'telegram', 'threads', 'upwork', 'soundcloud', 'snapchat', 'github', 'wechat', 'spotify', 'weibo', 'signal', 'line', 'instagram', 'leetcode', 'youtube', 'whatsapp', 'xing', 'dribbble', 'flickr', 'tumblr', 'vimeo', 'discord', 'behance', 'medium', 'bluesky', 'kakaotalk', 'x', 'kaggle', 'quora', 'devto', 'mastodon', 'fiverr', 'tiktok'}
