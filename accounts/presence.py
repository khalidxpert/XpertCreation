"""Marks a signed-in user as seen, in Redis, for five minutes.
The bell already polls from every page, so this needs no polling of its own."""
import time

from django.core.cache import cache

SEEN_SECONDS = 300


class PresenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            user = getattr(request, "user", None)
            if user is not None and user.is_authenticated:
                cache.set("seen:%d" % user.pk, int(time.time()), SEEN_SECONDS)
        except Exception:
            pass                      # presence must never break a request
        return response
