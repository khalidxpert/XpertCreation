from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils import timezone

from reminders.models import Birthday, Sent

WRAP = """<!DOCTYPE html>
<html><body style="margin:0;padding:24px;background:#F6F7FB;
 font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0D1424">
 <div style="max-width:460px;margin:0 auto;background:#fff;border-radius:16px;
      padding:26px;border:1px solid #E4E8F2">
  <div style="font-size:17px;font-weight:700;margin-bottom:16px">&#127874; XpertCreation</div>
  {body}
  <hr style="border:none;border-top:1px solid #E4E8F2;margin:22px 0">
  <p style="font-size:12px;color:#5A657C;line-height:1.5;margin:0">
   You saved this birthday yourself. Manage or remove it at
   <a href="https://xpertcreation.com/birthdays">xpertcreation.com/birthdays</a>.
  </p>
 </div></body></html>"""


class Command(BaseCommand):
    help = ("Emails birthday reminders. Meant to run once a day from cron. "
            "Safe to run more than once: each reminder is sent only once per year.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what would be sent, send nothing.")

    def handle(self, *args, **opts):
        today = timezone.localdate()
        dry = opts["dry_run"]
        sent = skipped = failed = 0

        for b in Birthday.objects.select_related("owner").iterator():
            when = b.next_occurrence(today)
            away = (when - today).days
            year = when.year

            kind = None
            if away == 0 and b.remind_on_day and b.last_dayof_year != year:
                kind = Sent.DAY_OF
            elif away == b.days_before and b.days_before > 0 and b.last_advance_year != year:
                kind = Sent.ADVANCE

            if not kind:
                continue

            # The person who saved the birthday is the only one contacted. The
            # birthday person never signed up here and must not be emailed.
            to = b.owner.email
            if not to or not b.owner.is_active:
                skipped += 1
                continue

            who = b.name
            age = b.turning
            if kind == Sent.DAY_OF:
                subject = "Today is %s's birthday" % who
                line = "<b>%s</b> turns %d today." % (who, age) if age \
                    else "It is <b>%s</b>'s birthday today." % who
            else:
                subject = "%s's birthday in %d days" % (who, away)
                line = "<b>%s</b> turns %d on %s, in %d days." % (who, age, b.pretty, away) if age \
                    else "<b>%s</b>'s birthday is on %s, in %d days." % (who, b.pretty, away)

            extra = ""
            if b.phone:
                extra += '<p style="font-size:14px;margin:0 0 6px">Phone: %s</p>' % b.phone
            if b.email:
                extra += '<p style="font-size:14px;margin:0 0 6px">Email: %s</p>' % b.email
            if b.note:
                extra += '<p style="font-size:13.5px;color:#5A657C;margin:8px 0 0">%s</p>' % b.note

            html = WRAP.format(body='<p style="font-size:16px;line-height:1.6;margin:0 0 12px">'
                                    + line + "</p>" + extra)
            text = "%s\n\n%s" % (subject, b.note or "")

            if dry:
                self.stdout.write("  would send [%s] %s -> %s" % (kind, who, to))
                sent += 1
                continue

            ok = True
            try:
                msg = EmailMultiAlternatives(
                    subject=subject, body=text,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None), to=[to])
                msg.attach_alternative(html, "text/html")
                msg.send(fail_silently=False)
            except Exception as exc:
                ok = False
                failed += 1
                self.stderr.write("  FAILED %s -> %s: %s" % (who, to, exc))

            try:
                Sent.objects.create(birthday=b, kind=kind, for_year=year, ok=ok)
            except IntegrityError:
                # Already logged for this year - another run got there first.
                continue

            # Marked even when the send failed, so a broken mailbox does not
            # produce the same failing email every day for a week.
            if kind == Sent.DAY_OF:
                b.last_dayof_year = year
                b.save(update_fields=["last_dayof_year"])
            else:
                b.last_advance_year = year
                b.save(update_fields=["last_advance_year"])

            if ok:
                sent += 1

        self.stdout.write(self.style.SUCCESS(
            "%s: sent %d, skipped %d, failed %d" % (today, sent, skipped, failed)))
