"""Links a new member to their referrer from the xc_ref cookie set by the /r/<username> page (stage 4).
Runs on any signed-in request, at most once per member (cached), and never breaks a request."""
from django.core.cache import cache

COOKIE = "xc_ref"


class ReferralMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            ref = request.COOKIES.get(COOKIE)
            user = getattr(request, "user", None)
            if ref and user is not None and user.is_authenticated:
                key = "rw:refdone:%d" % user.pk
                if not cache.get(key):
                    from rewards.views import attach_referral
                    attach_referral(user, ref)
                    cache.set(key, 1, 24 * 3600)
                response.delete_cookie(COOKIE, path="/")
        except Exception:
            pass                      # referral linking must never break a request
        return response
