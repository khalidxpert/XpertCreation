from django.core.management.base import BaseCommand
from django.utils import timezone

from companies.models import Company
from companies.views import _wipe_docs


class Command(BaseCommand):
    help = "Delete KYC documents 30 days after a company's review decision (the decision itself is kept)."

    def handle(self, *args, **o):
        old = timezone.now() - timezone.timedelta(days=30)
        n = 0
        for c in Company.objects.filter(status__in=[Company.APPROVED, Company.REJECTED], reviewed_at__lt=old).exclude(docs=None):
            _wipe_docs(c); n += 1
        self.stdout.write("companies with documents removed: %d" % n)
