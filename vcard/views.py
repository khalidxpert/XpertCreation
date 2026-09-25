from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import VisitingCard


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


def valid_url(u, host_hint=None):
    u = (u or "").strip()
    if not u:
        return ""
    if not u.startswith("https://"):
        return None
    if host_hint and host_hint not in u.lower():
        return None
    return u[:300]


def serialize(c, owner=False):
    out = {
        "display_name": c.display_name, "role": c.role, "org": c.org,
        "city": c.city, "theme": c.theme, "token": c.token,
        "avatar": c.user.avatar,
        "email": c.user.email if c.show_email else "",
    }
    if c.show_phone:
        out["phone"] = c.phone
    if c.show_whatsapp:
        out["whatsapp"] = c.whatsapp
    out["linkedin"] = c.linkedin
    out["instagram"] = c.instagram
    out["twitter"] = c.twitter
    out["website"] = c.website
    if owner:
        out["is_public"] = c.is_public
        out["show_phone"] = c.show_phone
        out["show_email"] = c.show_email
        out["show_whatsapp"] = c.show_whatsapp
    return out


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def my_card(request):
    card = VisitingCard.objects.filter(user=request.user).select_related("user").first()

    if request.method == "DELETE":
        if card:
            card.delete()
        return Response({"detail": "Removed."})

    if request.method == "GET":
        return Response({"card": serialize(card, owner=True) if card else None})

    d = request.data
    li = valid_url(d.get("linkedin"), "linkedin.com")
    ig = valid_url(d.get("instagram"), "instagram.com")
    tw = valid_url(d.get("twitter"), "twitter.com") or valid_url(d.get("twitter"), "x.com")
    web = valid_url(d.get("website"))

    for label, raw, parsed in (("LinkedIn", d.get("linkedin"), li),
                               ("Instagram", d.get("instagram"), ig),
                               ("Twitter/X", d.get("twitter"), tw),
                               ("Website", d.get("website"), web)):
        if raw and str(raw).strip() and parsed is None:
            return _err("That doesn't look like a valid %s link (needs https://)." % label)

    display_name = str(d.get("display_name") or "").strip()[:100]
    if not display_name:
        display_name = (request.user.full_name or "").strip() or \
                       request.user.email.split("@")[0]

    theme = d.get("theme")
    if theme not in dict(VisitingCard.THEMES):
        theme = "ink"

    if not card:
        card = VisitingCard(user=request.user)

    card.display_name = display_name
    card.role = str(d.get("role") or "").strip()[:100]
    card.org = str(d.get("org") or "").strip()[:100]
    card.city = str(d.get("city") or "").strip()[:60]
    card.phone = str(d.get("phone") or "").strip()[:32]
    card.whatsapp = str(d.get("whatsapp") or "").strip()[:32]
    card.show_phone = bool(d.get("show_phone")) and bool(card.phone)
    card.show_email = bool(d.get("show_email", True))
    card.show_whatsapp = bool(d.get("show_whatsapp")) and bool(card.whatsapp)
    card.linkedin = li or ""
    card.instagram = ig or ""
    card.twitter = tw or ""
    card.website = web or ""
    card.theme = theme
    card.is_public = bool(d.get("is_public", True))
    card.save()

    return Response({"card": serialize(card, owner=True), "detail": "Saved."},
                    status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def public_card(request, token):
    """Read by anyone with the link - the token is the whole access control,
    same pattern as the ticket links."""
    card = VisitingCard.objects.filter(token=token, is_public=True) \
                               .select_related("user").first()
    if not card:
        return _err("That card is not available.", status.HTTP_404_NOT_FOUND)
    return Response({"card": serialize(card, owner=False)})
