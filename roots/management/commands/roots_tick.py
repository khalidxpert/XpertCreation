"""Daily (morning): tell family members about today's birthdays, wedding anniversaries and barsi (death anniversary),
and about board events / reminders that are tomorrow."""
import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from roots.models import Membership, Notice, Person


def _tell(fid, text, link, skip=None):
    try:
        from notifications.views import notify
    except Exception:
        return 0
    n = 0
    for m in Membership.objects.filter(family_id=fid).exclude(role=Membership.PENDING).select_related("user")[:500]:
        if m.user_id != skip:
            notify(m.user, "roots", text, link); n += 1
    return n


class Command(BaseCommand):
    help = "Roots of Love daily reminders"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="run even if already run today / before 8 am")

    def handle(self, *a, **k):
        today = timezone.localdate()
        mark = os.environ.get("XC_ROOTS_MARK", "/var/lib/gunicorn-academy/roots_tick.last")
        if not k.get("force"):
            if timezone.localtime().hour < 8:
                return
            try:
                if open(mark).read().strip() == today.isoformat():
                    return
            except OSError:
                pass
        try:
            open(mark, "w").write(today.isoformat())
        except OSError:
            pass
        sent = 0
        ppl = Person.objects.select_related("family")
        for p in ppl.filter(alive=True, born__month=today.month, born__day=today.day):
            age = today.year - p.born.year
            sent += _tell(p.family_id, "\U0001F382 Today is %s's birthday%s (%s). Send your duas!" % (p.name, " - %d years" % age if 0 < age < 130 else "", p.family.name),
                          "/roots#f%d/p%d" % (p.family_id, p.id), skip=p.user_id)
        for p in ppl.filter(alive=True, married__month=today.month, married__day=today.day, gender="m").exclude(spouse=None):
            sent += _tell(p.family_id, "\U0001F48D Today is the wedding anniversary of %s and %s (%s)." % (p.name, p.spouse.name, p.family.name), "/roots#f%d/p%d" % (p.family_id, p.id))
        for p in ppl.filter(alive=False, died__month=today.month, died__day=today.day):
            sent += _tell(p.family_id, "\U0001F932 Today is the barsi of %s (%s). Remember them in your duas." % (p.name, p.family.name), "/roots#f%d/p%d" % (p.family_id, p.id))
        for n in Notice.objects.filter(day=today + timedelta(days=1), told=False).select_related("family"):
            sent += _tell(n.family_id, "\U0001F4C5 Tomorrow (%s): %s" % (n.family.name, n.text[:120]), "/roots#f%d/board" % n.family_id)
            n.told = True; n.save(update_fields=["told"])
        self.stdout.write("%s roots_tick: %d notifications" % (timezone.now().strftime("%Y-%m-%d %H:%M"), sent))
