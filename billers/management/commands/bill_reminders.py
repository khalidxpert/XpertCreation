"""Every morning: remind members 3 days before and on the due day of each saved bill (email + in-app notification)."""
import importlib
from datetime import date, timedelta

from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from billers.models import Biller
from billers.views import bill_link, company_name, next_due


def _notify():
    for mod in ("notifications.utils", "notifications.views", "notifications.models", "notifications.notify", "notifications"):
        try:
            f = getattr(importlib.import_module(mod), "notify", None)
            if callable(f):
                return f
        except Exception:
            continue
    return None


class Command(BaseCommand):
    help = "Send bill reminders (3 days before and on the due day)."

    def handle(self, *a, **o):
        today = date.today(); notify = _notify(); sent = 0
        for b in Biller.objects.filter(remind=True).select_related("user"):
            due = next_due(b.due_day, today); left = (due - today).days
            if left not in (3, 0) or b.last_reminded == today:
                continue
            when = "today" if left == 0 else "in 3 days (%s)" % due.strftime("%-d %B")
            text = "Your %s bill (%s) is due %s." % (company_name(b.company), b.nickname, when)
            link = bill_link(b.company, b.ref)
            if notify:
                try:
                    notify(b.user, "bill", text, "/bills")
                except Exception:
                    pass
            if getattr(b.user, "email", ""):
                try:
                    send_mail("Bill reminder: %s due %s" % (b.nickname, "today" if left == 0 else "in 3 days"),
                              "%s\n\nView your bill: %s\n\nManage your billers: https://xpertcreation.com/bills\n\nXpertCreation" % (text, link), None, [b.user.email])
                except Exception as e:
                    self.stderr.write("email to user %s failed: %s" % (b.user_id, e))
            b.last_reminded = today; b.save(update_fields=["last_reminded"]); sent += 1
        self.stdout.write("bill reminders sent: %d" % sent)
