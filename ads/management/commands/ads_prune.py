from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ads.models import AdEvent


class Command(BaseCommand):
    help = "Delete raw ad events older than 30 days (daily totals are kept)."

    def handle(self, *args, **kwargs):
        n, _ = AdEvent.objects.filter(created_at__lt=timezone.now() - timedelta(days=30)).delete()
        self.stdout.write("%s ads_prune: deleted %d" % (timezone.now().isoformat(timespec="seconds"), n))
