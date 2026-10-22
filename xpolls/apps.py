import re

from django.apps import AppConfig


class XpollsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "xpolls"
    verbose_name = "XpertChat polls"

    def ready(self):
        # chat list previews and phone notifications: hide the [poll:N] / [event:...] / [loc] / [contact] markers too
        try:
            from notifications import msgx
            msgx.MARK = re.compile(r"^\s*(?:\[re:\d+\]|\[fwd\]|\[poll:\d+\]|\[event:[0-9TZ:.\-]+\]|\[loc\]|\[contact:[\w.-]*\])\s*")
        except Exception:
            pass
