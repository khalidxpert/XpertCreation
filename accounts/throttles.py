from rest_framework.throttling import SimpleRateThrottle


class _EmailOrIPThrottle(SimpleRateThrottle):
    """
    Throttles on the submitted email when present, otherwise on IP.

    Keying on email matters: an attacker rotating IPs still gets stopped from
    hammering one account, and a single office NAT does not lock out everyone.
    """

    scope = "override_me"

    def get_cache_key(self, request, view):
        email = ""
        if request.method == "POST" and isinstance(request.data, dict):
            email = (request.data.get("email") or "").lower().strip()
        ident = email or self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginThrottle(_EmailOrIPThrottle):
    scope = "login"


class RegisterThrottle(SimpleRateThrottle):
    """Signup is IP keyed. Stops one host from farming accounts."""

    scope = "register"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class CodeSendThrottle(_EmailOrIPThrottle):
    """Sending codes costs money and can be used to spam a victim's inbox."""

    scope = "code_send"


class CodeCheckThrottle(_EmailOrIPThrottle):
    scope = "code_check"
