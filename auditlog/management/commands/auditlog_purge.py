from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from auditlog.models import AuditEvent


class Command(BaseCommand):
    help = "Delete system log lines older than 180 days."

    def handle(self, *args, **opts):
        n = AuditEvent.objects.filter(created_at__lt=timezone.now() - timedelta(days=180)).delete()[0]
        self.stdout.write("system log lines removed: %d" % n)
