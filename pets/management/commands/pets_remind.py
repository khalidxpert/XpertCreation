"""Daily: bell reminders for vaccines and check-ups due within three days, and expire old
lost & found posts. Each due date is reminded once."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import F, Q
from django.utils import timezone

from notifications.views import notify
from pets.models import HealthRecord, LostFound


class Command(BaseCommand):
    help = "Send pet health reminders and expire old lost & found posts."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        qs = (HealthRecord.objects
              .filter(next_due__isnull=False, next_due__lte=today + timedelta(days=3),
                      next_due__gte=today - timedelta(days=7), pet__owner__is_active=True)
              .filter(Q(reminded_for__isnull=True) | ~Q(reminded_for=F("next_due")))
              .select_related("pet", "pet__owner"))
        sent = 0
        for r in qs:
            days = (r.next_due - today).days
            when = "today" if days == 0 else ("tomorrow" if days == 1 else
                   ("in %d days" % days if days > 1 else "overdue since %s" % r.next_due.strftime("%d %b")))
            notify(r.pet.owner, "pet", "%s: %s is due %s" % (r.pet.name, r.title, when), "/pets#pet-%d" % r.pet_id)
            r.reminded_for = r.next_due
            r.save(update_fields=["reminded_for"])
            sent += 1
        expired = LostFound.objects.filter(status="active", expires_at__lt=timezone.now()).update(status="expired")
        self.stdout.write("reminders sent: %d, lost & found expired: %d" % (sent, expired))
