"""Interests and privacy: who can find me, who can send me requests, optional gender, women/men-only groups."""
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import GroupRule, Pref

INTERESTS = [("cricket", "Cricket", "\U0001F3CF"), ("football", "Football", "\u26BD"), ("technology", "Technology", "\U0001F4BB"),
             ("programming", "Programming", "\U0001F468\u200D\U0001F4BB"), ("ai", "AI", "\U0001F916"), ("business", "Business", "\U0001F4BC"),
             ("jobs", "Jobs and careers", "\U0001F9D1\u200D\U0001F4BC"), ("freelancing", "Freelancing", "\U0001F9FE"), ("education", "Education", "\U0001F393"),
             ("ielts", "English and IELTS", "\U0001F1EC\U0001F1E7"), ("design", "Design", "\U0001F3A8"), ("photography", "Photography", "\U0001F4F7"),
             ("cooking", "Cooking", "\U0001F373"), ("fashion", "Fashion", "\U0001F457"), ("fitness", "Fitness", "\U0001F3CB\uFE0F"),
             ("travel", "Travel", "\u2708\uFE0F"), ("pets", "Pets", "\U0001F43E"), ("dramas", "Dramas and films", "\U0001F3AC"), ("music", "Music", "\U0001F3B5"),
             ("gaming", "Gaming", "\U0001F3AE"), ("cars", "Cars", "\U0001F697"), ("realestate", "Property", "\U0001F3E0"), ("health", "Health", "\U0001FA7A"),
             ("books", "Books", "\U0001F4DA")]
KEYS = {k for k, _, _ in INTERESTS}


def _pref(u):
    p, _ = Pref.objects.get_or_create(user=u)
    return p


def _gender(u):
    p = Pref.objects.filter(user=u).values_list("gender", flat=True).first()
    return p or ""


def _conn(u):
    try:
        from feed.views import _connected_ids
        return set(_connected_ids(u))
    except Exception:
        return set()


def hide_from_search(qs, viewer, field="user"):
    """Leave out people who chose not to be found by this viewer. field: the user field on qs (None = qs is users)."""
    pre = (field + "__") if field else ""
    me = viewer.pk if viewer.is_authenticated else 0
    g = _gender(viewer) if me else ""
    conn = _conn(viewer) if me else set()
    own = Q(**{(field + "_id") if field else "pk": me})
    hide_conn = Q(**{pre + "xpref__find": "connections"}) & ~Q(**{(field + "_id__in") if field else "pk__in": list(conn)})
    hide_same = Q(**{pre + "xpref__find": "same"}) & ~Q(**{pre + "xpref__gender": g or "-none-"})
    return qs.exclude((hide_conn | hide_same) & ~own)


def may_request(sender, to):
    """'' if sender may send a connection request to 'to', otherwise the reason."""
    p = Pref.objects.filter(user=to).first()
    if not p or p.requests == "everyone":
        return ""
    if p.requests == "nobody":
        return "This member is not accepting connection requests."
    if p.requests == "same" and (not p.gender or _gender(sender) != p.gender):
        return "This member only accepts requests from some people."
    return ""


def may_join(group, user):
    """'' if user may be in this group, otherwise the reason (women-only / men-only groups)."""
    r = GroupRule.objects.filter(group=group).first()
    if not r or not r.only:
        return ""
    if _gender(user) != r.only:
        return "This group is for %s only." % ("women" if r.only == "female" else "men")
    return ""


def on_group_create(group, data):
    only = str(data.get("only") or "")
    if only in ("male", "female") and _gender(group.created_by) == only:
        GroupRule.objects.update_or_create(group=group, defaults={"only": only})


def group_only(group):
    r = GroupRule.objects.filter(group=group).first()
    return r.only if r else ""


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def me(request):
    p = _pref(request.user)
    if request.method == "POST":
        d = request.data
        if "gender" in d:
            p.gender = d.get("gender") if d.get("gender") in ("male", "female") else ""
        if "find" in d and d.get("find") in ("everyone", "same", "connections"):
            p.find = d.get("find")
        if "requests" in d and d.get("requests") in ("everyone", "same", "nobody"):
            p.requests = d.get("requests")
        if "interests" in d:
            p.interests = [k for k in (d.get("interests") or []) if k in KEYS][:12]
        if (p.find == "same" or p.requests == "same") and not p.gender:
            return Response({"detail": "To use 'same gender only', choose your gender first (it stays private)."}, status=400)
        p.save()
    return Response({"gender": p.gender, "find": p.find, "requests": p.requests, "interests": p.interests,
                     "catalog": [{"key": k, "label": l, "icon": i} for k, l, i in INTERESTS]})
