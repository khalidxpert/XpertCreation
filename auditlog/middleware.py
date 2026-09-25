"""Writes a line to the system log for every change a member makes through the API (and sign-ins,
sign-outs, failed sign-ins). Reading pages is not logged, and nothing a person wrote is copied."""
import json
import re

from .models import AuditEvent

SKIP = re.compile(r"(/typing/|/api/auth/csrf/|/api/notify/read/|/api/notify/clear/|/flip/|/move/|/heartbeat/|/presence/|"
                  r"/api/typing/|/keystroke|/api/games/.*/(guess|tap|step)/)")

# (method, path pattern, what it means, category). The first match wins.
RULES = [
    ("POST", r"^/api/auth/login/", "Signed in", "account"),
    ("POST", r"^/api/auth/logout/", "Signed out", "account"),
    ("POST", r"^/api/auth/(register|signup)/", "Started sign-up", "account"),
    ("POST", r"^/api/auth/verify", "Verified email", "account"),
    ("POST", r"^/api/auth/(password|reset|forgot)", "Password reset", "account"),
    ("POST", r"^/api/auth/.*(delete|remove)", "Deleted account", "account"),
    ("POST", r"^/api/auth/.*avatar", "Changed profile picture", "account"),
    ("*", r"^/api/auth/me/", "Updated account details", "account"),
    ("POST", r"^/api/network/me/skills/", "Changed skills", "connect"),
    ("POST", r"^/api/network/me/(experience|education)/", "Edited experience or education", "connect"),
    ("POST", r"^/api/network/me/requests/\d+/accept", "Accepted a connection request", "connect"),
    ("POST", r"^/api/network/me/requests/\d+/", "Answered a connection request", "connect"),
    ("POST", r"^/api/network/me/tick/", "Applied for the blue tick", "connect"),
    ("*", r"^/api/network/me/", "Edited professional profile", "connect"),
    ("POST", r"^/api/network/in/[^/]+/connect/", "Sent a connection request", "connect"),
    ("POST", r"^/api/network/in/[^/]+/disconnect/", "Removed a connection", "connect"),
    ("POST", r"^/api/network/in/[^/]+/follow/", "Followed or unfollowed someone", "connect"),
    ("POST", r"^/api/network/in/[^/]+/endorse/", "Endorsed a skill", "connect"),
    ("POST", r"^/api/network/in/[^/]+/message/", "Opened a chat", "chat"),
    ("POST", r"^/api/network/in/[^/]+/report/", "Reported a profile", "report"),
    ("POST", r"^/api/notify/threads/\d+/block/", "Blocked or unblocked in chat", "chat"),
    ("POST", r"^/api/notify/threads/\d+/report/", "Reported a chat", "report"),
    ("POST", r"^/api/notify/threads/\d+/clear/", "Cleared or deleted a chat", "chat"),
    ("POST", r"^/api/notify/threads/delete/", "Deleted chats", "chat"),
    ("POST", r"^/api/notify/threads/\d+/disappear/", "Changed disappearing messages", "chat"),
    ("POST", r"^/api/notify/threads/\d+/", "Sent a chat message", "chat"),
    ("POST", r"^/api/notify/threads/start/", "Started a chat", "chat"),
    ("POST", r"^/api/notify/push/subscribe/", "Turned on phone notifications", "account"),
    ("POST", r"^/api/notify/push/unsubscribe/", "Turned off phone notifications", "account"),
    ("POST", r"^/api/feed/posts/\d+/react/", "Reacted to a post", "feed"),
    ("POST", r"^/api/feed/posts/\d+/comments/", "Commented on a post", "feed"),
    ("POST", r"^/api/feed/posts/\d+/report/", "Reported a post", "report"),
    ("DELETE", r"^/api/feed/comments/", "Deleted a comment", "feed"),
    ("PATCH", r"^/api/feed/comments/", "Hid or showed a comment (moderator)", "moderation"),
    ("POST", r"^/api/feed/posts/$", "Posted in the feed", "feed"),
    ("PATCH", r"^/api/feed/posts/\d+/", "Edited or hid a post", "feed"),
    ("DELETE", r"^/api/feed/posts/\d+/", "Deleted a post", "feed"),
    ("POST", r"^/api/jobs/$", "Posted a job", "jobs"),
    ("POST", r"^/api/jobs/\d+/apply/", "Applied for a job", "jobs"),
    ("POST", r"^/api/jobs/\d+/withdraw/", "Withdrew a job application", "jobs"),
    ("POST", r"^/api/jobs/applications/\d+/status/", "Shortlisted or turned down an applicant", "jobs"),
    ("POST", r"^/api/jobs/\d+/report/", "Reported a job", "report"),
    ("PATCH", r"^/api/jobs/\d+/", "Edited, closed or hid a job", "jobs"),
    ("DELETE", r"^/api/jobs/\d+/", "Deleted a job", "jobs"),
    ("POST", r"^/api/pets/adopt/\d+/request/", "Asked to adopt a pet", "pets"),
    ("POST", r"^/api/pets/adopt/requests/\d+/accept/", "Accepted an adoption request", "pets"),
    ("POST", r"^/api/pets/adopt/requests/\d+/", "Answered an adoption request", "pets"),
    ("POST", r"^/api/pets/adopt/$", "Listed a pet for adoption", "pets"),
    ("POST", r"^/api/pets/adopt/", "Changed an adoption listing", "pets"),
    ("POST", r"^/api/pets/vets/$", "Added a vet", "pets"),
    ("*", r"^/api/pets/vets/\d+/", "Approved or removed a vet (moderator)", "moderation"),
    ("POST", r"^/api/pets/tag/[^/]+/found/", "Left a note on a pet tag", "pets"),
    ("POST", r"^/api/pets/lost/", "Posted or updated lost & found", "pets"),
    ("POST", r"^/api/pets/mine/", "Added a pet", "pets"),
    ("POST", r"^/api/pets/", "Updated pet records", "pets"),
    ("POST", r"^/api/screen/.*review", "Reviewed a show", "shows"),
    ("POST", r"^/api/screen/.*list", "Changed watchlist", "shows"),
    ("POST", r"^/api/academy/.*(certificate|cert)", "Earned a certificate", "academy"),
    ("POST", r"^/api/academy/.*(quiz|answer|grade)", "Answered a quiz", "academy"),
    ("POST", r"^/api/academy/", "Learning progress", "academy"),
    ("POST", r"^/api/blood", "Blood bank", "blood"),
    ("POST", r"^/api/donat", "Donations", "donations"),
    ("POST", r"^/api/games/", "Played a game", "games"),
    ("POST", r"^/api/typing", "Typing tutor", "games"),
    ("*", r"^/api/moderation/", "Moderation action", "moderation"),
    ("POST", r"^/admin/", "Changed data in Django admin", "admin"),
]
RULES = [(m, re.compile(p), a, c) for m, p, a, c in RULES]


def _ip(request):
    ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("HTTP_X_REAL_IP") \
        or (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    return ip or None


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        method = request.method
        email = ""
        if method == "POST" and path.startswith("/api/auth/login/"):
            try:                         # only the address, for failed sign-ins - never the password
                email = str(json.loads(request.body or b"{}").get("email") or "")[:120]
            except Exception:
                email = ""
        response = self.get_response(request)
        try:
            if method in ("POST", "PUT", "PATCH", "DELETE") and (path.startswith("/api/") or path.startswith("/admin/")) \
                    and not SKIP.search(path):
                self._log(request, response, path, method, email)
        except Exception:
            pass                          # the log must never break the site
        return response

    def _log(self, request, response, path, method, email):
        status = getattr(response, "status_code", 0)
        failed_login = path.startswith("/api/auth/login/") and status >= 400
        if status >= 400 and not failed_login:
            return
        u = getattr(request, "user", None)
        user = u if (u is not None and u.is_authenticated) else None
        action, cat = None, "other"
        for m, rx, a, c in RULES:
            if (m == "*" or m == method) and rx.search(path):
                action, cat = a, c
                break
        if failed_login:
            action, cat = "Failed sign-in", "security"
        if not action:
            parts = [p for p in path.split("/") if p and p != "api"]
            action, cat = "%s: %s" % ((parts[0] if parts else "site").capitalize(), method.lower()), "other"
        nums = re.findall(r"/(\d+)(?=/)", path)
        AuditEvent.objects.create(
            user=user, action=action[:80], category=cat, method=method, path=re.sub(r"\d+", "#", path)[:200],
            object_id=nums[0] if nums else "", status=status, ip=_ip(request),
            agent=(request.META.get("HTTP_USER_AGENT") or "")[:160], extra=email if failed_login else "")
