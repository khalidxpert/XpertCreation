import logging

from django.contrib.auth import get_user_model
from django.db.models import Max
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import ModApplication, Ticket, TicketMessage

log = logging.getLogger(__name__)
User = get_user_model()


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


def is_super(user):
    return user.is_authenticated and user.is_superuser


def is_staff_user(user):
    return user.is_authenticated and (user.is_superuser or user.is_moderator)


class ApplyThrottle(SimpleRateThrottle):
    scope = "modapply"
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated: return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class TicketThrottle(SimpleRateThrottle):
    scope = "ticket"
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated: return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def valid_url(u, host_hint):
    """A link has to at least point at the site it claims to."""
    u = (u or "").strip()
    if not u:
        return ""
    if not u.startswith("https://"):
        return None
    if host_hint not in u.lower():
        return None
    return u[:300]


# ---------------------------------------------------------------- applying

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ApplyThrottle])
def apply(request):
    """Sign-in only, one application per account."""
    existing = ModApplication.objects.filter(user=request.user).first()

    if request.method == "GET":
        return Response({"application": {
            "state": existing.state, "why": existing.why,
            "linkedin": existing.linkedin, "instagram": existing.instagram,
            "twitter": existing.twitter,
        } if existing else None, "is_moderator": request.user.is_moderator})

    if request.user.is_moderator:
        return _err("You are already a moderator.")
    if existing and existing.state == ModApplication.PENDING:
        return _err("Your application is already waiting for a decision.")

    why = str(request.data.get("why") or "").strip()
    if len(why) < 20:
        return _err("Say a bit more about why you'd like to help \u2014 a couple of sentences.")

    li = valid_url(request.data.get("linkedin"), "linkedin.com")
    ig = valid_url(request.data.get("instagram"), "instagram.com")
    tw = valid_url(request.data.get("twitter"), "twitter.com") \
         or valid_url(request.data.get("twitter"), "x.com")

    for label, val in (("LinkedIn", request.data.get("linkedin")),
                       ("Instagram", request.data.get("instagram")),
                       ("Twitter/X", request.data.get("twitter"))):
        if val and val.strip() and locals()[
            {"LinkedIn":"li","Instagram":"ig","Twitter/X":"tw"}[label]] is None:
            return _err("That doesn't look like a %s link." % label)

    app, _created = ModApplication.objects.update_or_create(
        user=request.user,
        defaults=dict(why=why[:800], linkedin=li or "", instagram=ig or "",
                     twitter=tw or "", state=ModApplication.PENDING,
                     decided_at=None, decided_by=None))

    return Response({"detail": "Sent. You will see a decision here once "
                     "someone has read it."}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def applications(request):
    """Waiting applications. Super admin only."""
    if not is_super(request.user):
        return _err("Not allowed.", status.HTTP_403_FORBIDDEN)

    rows = (ModApplication.objects.filter(state=ModApplication.PENDING)
            .select_related("user").order_by("created_at"))
    return Response({"applications": [{
        "id": a.id,
        "name": (a.user.full_name or "").strip() or a.user.email.split("@")[0],
        "email": a.user.email, "avatar": a.user.avatar,
        "why": a.why, "linkedin": a.linkedin, "instagram": a.instagram,
        "twitter": a.twitter,
        "when": a.created_at.strftime("%d %b %Y"),
    } for a in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decide_application(request, pk):
    """body: { accept: true|false }"""
    if not is_super(request.user):
        return _err("Not allowed.", status.HTTP_403_FORBIDDEN)

    app = ModApplication.objects.filter(id=pk, state=ModApplication.PENDING) \
                                .select_related("user").first()
    if not app:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)

    accept = bool(request.data.get("accept"))
    app.state = ModApplication.ACCEPTED if accept else ModApplication.DECLINED
    app.decided_at = timezone.now()
    app.decided_by = request.user
    app.save()

    if accept:
        app.user.is_moderator = True
        app.user.moderator_since = timezone.now()
        app.user.save(update_fields=["is_moderator", "moderator_since"])

    return Response({"detail": "Accepted." if accept else "Declined."})


@api_view(["GET"])
@permission_classes([AllowAny])
def team(request):
    """
    The public team page: the super admin, then accepted moderators who chose
    to share a social link. No email anywhere on this page.
    """
    boss = User.objects.filter(is_superuser=True).first()
    rows = []
    if boss:
        rows.append({
            "name": (boss.full_name or "").strip() or "Founder",
            "role": "Founder & CEO", "avatar": boss.avatar,
            "linkedin": "", "instagram": "", "twitter": "",
        })

    apps = (ModApplication.objects.filter(state=ModApplication.ACCEPTED)
            .select_related("user").order_by("decided_at"))
    for a in apps:
        if not a.user.is_moderator:
            continue
        rows.append({
            "name": (a.user.full_name or "").strip() or "Moderator",
            "role": "Moderator", "avatar": a.user.avatar,
            "linkedin": a.linkedin, "instagram": a.instagram, "twitter": a.twitter,
        })
    return Response({"team": rows})


# ---------------------------------------------------------------- roles (super admin toggles)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def role_settings(request):
    """What a moderator is allowed to do. One flag today (reviews); room for
    more without changing the shape."""
    if not is_super(request.user):
        return _err("Not allowed.", status.HTTP_403_FORBIDDEN)

    rows = User.objects.filter(is_moderator=True).order_by("moderator_since")
    return Response({"moderators": [{
        "id": m.id, "email": m.email,
        "name": (m.full_name or "").strip() or m.email.split("@")[0],
        "can_reviews": True,   # the only permission that exists so far
        "can_tickets": bool(getattr(m, "can_moderate_tickets", True)),
    } for m in rows]})


# ---------------------------------------------------------------- support tickets

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([TicketThrottle])
def tickets(request):
    if request.method == "GET":
        if is_staff_user(request.user):
            qs = Ticket.objects.exclude(state=Ticket.CLOSED).select_related("user")
        else:
            qs = Ticket.objects.filter(user=request.user)
        rows = qs.order_by("-updated_at")[:60]
        return Response({"tickets": [{
            "id": t.id, "subject": t.subject, "priority": t.priority,
            "state": t.state,
            "from": (t.user.full_name or "").strip() or t.user.email.split("@")[0]
                    if is_staff_user(request.user) else None,
            "updated": t.updated_at.strftime("%d %b, %H:%M"),
            "messages": t.messages.count(),
        } for t in rows], "is_staff": is_staff_user(request.user)})

    subject = str(request.data.get("subject") or "").strip()[:200]
    body = str(request.data.get("message") or "").strip()
    if len(subject) < 3:
        return _err("Give it a short subject.")
    if len(body) < 10:
        return _err("Tell us a bit more \u2014 at least a sentence.")

    t = Ticket.objects.create(user=request.user, subject=subject)
    TicketMessage.objects.create(ticket=t, author=request.user, body=body[:4000])
    return Response({"id": t.id, "detail": "Opened. We'll reply here."},
                    status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ticket_detail(request, pk):
    t = Ticket.objects.filter(id=pk).select_related("user").first()
    if not t:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)

    staff = is_staff_user(request.user)
    if not staff and t.user_id != request.user.id:
        return _err("Not your ticket.", status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        msgs = t.messages.select_related("author")
        return Response({
            "id": t.id, "subject": t.subject, "state": t.state,
            "priority": t.priority,
            "from": (t.user.full_name or "").strip() or t.user.email.split("@")[0],
            "messages": [{
                "body": m.body, "staff": m.is_staff,
                "author": (m.author.full_name or "").strip() or m.author.email.split("@")[0],
                "when": m.created_at.strftime("%d %b, %H:%M"),
            } for m in msgs],
        })

    body = str(request.data.get("message") or "").strip()
    close = request.data.get("close")

    if body:
        if len(body) < 2:
            return _err("Write something first.")
        TicketMessage.objects.create(ticket=t, author=request.user,
                                     is_staff=staff, body=body[:4000])
        t.state = Ticket.ANSWERED if staff else Ticket.OPEN
        t.save(update_fields=["state", "updated_at"])

    if close is not None and (staff or t.user_id == request.user.id):
        t.state = Ticket.CLOSED if close else Ticket.OPEN
        t.save(update_fields=["state", "updated_at"])

    return Response({"detail": "Sent."})
