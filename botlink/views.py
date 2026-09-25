import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import BotLink, LinkCode

log = logging.getLogger(__name__)


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


class CodeThrottle(SimpleRateThrottle):
    scope = "botcode"
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


# ---------------------------------------------------------------- the person, in-app

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_links(request):
    rows = BotLink.objects.filter(user=request.user)
    return Response({"links": [{
        "platform": r.platform, "name": r.external_name,
        "since": r.linked_at.strftime("%d %b %Y"),
    } for r in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([CodeThrottle])
def make_code(request):
    """body: { platform: "discord"|"telegram" }"""
    platform = request.data.get("platform")
    if platform not in dict(LinkCode.PLATFORMS):
        return _err("Unknown platform.")

    if BotLink.objects.filter(user=request.user, platform=platform).exists():
        return _err("Already connected. Disconnect first if you want to relink.")

    # An old unused code for the same platform is replaced rather than piling
    # up - only the newest one should work.
    LinkCode.objects.filter(user=request.user, platform=platform, used_at=None).delete()
    c = LinkCode.objects.create(user=request.user, platform=platform)

    return Response({"code": c.code, "expires_in": 600})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unlink(request):
    """body: { platform: "discord"|"telegram" }"""
    platform = request.data.get("platform")
    n = BotLink.objects.filter(user=request.user, platform=platform).delete()[0]
    return Response({"detail": "Disconnected." if n else "Nothing to disconnect."})


# ---------------------------------------------------------------- the bot, server-to-server

def _check_bot_secret(request, setting_name):
    from django.conf import settings
    expected = getattr(settings, setting_name, "")
    if not expected:
        return False
    # Discord's caller sends this as a header; PenFlow's Telegram bot follows
    # its own _post() pattern and puts it in the JSON body instead (the same
    # way it already sends bot_secret to PenFlow's own verify endpoint) - so
    # both are accepted rather than assuming one transport for every caller.
    got = request.META.get("HTTP_X_BOT_SECRET", "") or str(request.data.get("bot_secret") or "")
    return got == expected


@api_view(["POST"])
@permission_classes([AllowAny])
def bot_verify(request):
    """
    Called by the bot process itself, never by a browser - authenticated by
    a shared secret in a header, the same pattern PenFlow's own Discord
    integration already uses.

    body: { platform, code, external_id, external_name, secret_setting }
    """
    platform = request.data.get("platform")
    if platform not in dict(LinkCode.PLATFORMS):
        return _err("Unknown platform.")

    setting_name = "DISCORD_BOT_SECRET" if platform == "discord" else "TELEGRAM_BOT_SECRET"
    if not _check_bot_secret(request, setting_name):
        return _err("Not authorised.", status.HTTP_403_FORBIDDEN)

    code = str(request.data.get("code") or "").strip().upper()
    external_id = str(request.data.get("external_id") or "").strip()
    external_name = str(request.data.get("external_name") or "")[:100]

    if not code or not external_id:
        return _err("Missing code or id.")

    c = (LinkCode.objects.filter(platform=platform, code=code, used_at=None)
        .order_by("-created_at").first())
    if not c:
        return _err("That code is not valid. Codes expire after 10 minutes.")
    if c.expired:
        return _err("That code has expired. Generate a new one on the site.")

    c.used_at = timezone.now()
    c.save(update_fields=["used_at"])

    BotLink.objects.update_or_create(
        user=c.user, platform=platform,
        defaults={"external_id": external_id, "external_name": external_name,
                 "linked_at": timezone.now()})

    who = (c.user.full_name or "").strip() or c.user.email.split("@")[0]
    return Response({"detail": "Linked.", "name": who, "email": c.user.email})
