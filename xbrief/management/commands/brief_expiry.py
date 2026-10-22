"""Bell + phone reminders for documents that are about to expire (ID card, passport, licence...).
Runs once a day from /etc/cron.d/xc-briefcase. Each stage (60, 30, 7 days, the day itself) is sent once;
if a stage was missed (server off, date added late) only the nearest one goes, never a burst."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from xbrief.models import Doc

STAGES = (60, 30, 7, 0)


class Command(BaseCommand):
    help = "Send My Briefcase expiry reminders"

    def handle(self, *a, **kw):
        from notifications.views import notify
        today = timezone.localdate()
        sent = 0
        for d in Doc.objects.filter(expires__isnull=False, expires__gte=today, expires__lte=today + timezone.timedelta(days=60)).select_related("owner"):
            left = (d.expires - today).days
            done = set(x for x in d.reminded.split(",") if x)
            due = [s for s in STAGES if left <= s and str(s) not in done]
            if not due:
                continue
            stage = min(due)
            when = d.expires.strftime("%d %b %Y")
            if stage == 0:
                text = "⏰ \"%s\" expires today (%s). Renew it now." % (d.title, when)
            else:
                text = "⏰ \"%s\" expires in %d day%s (%s). Start the renewal in time." % (d.title, left, "" if left == 1 else "s", when)
            try:
                notify(d.owner, "briefcase", text, "/briefcase#d%d" % d.id)
                sent += 1
            except Exception as e:
                self.stderr.write("doc %d: %s" % (d.id, e))
                continue
            done.update(str(s) for s in STAGES if s >= stage)
            Doc.objects.filter(pk=d.pk).update(reminded=",".join(sorted(done, key=int)))
        self.stdout.write("%s reminders sent: %d" % (timezone.now().strftime("%Y-%m-%d %H:%M"), sent))
