from django.core.management.base import BaseCommand

from kids.models import KidsChannel
from kids.views import refresh


class Command(BaseCommand):
    help = "Pull the latest videos of every active Kids channel."

    def handle(self, *a, **o):
        n = 0
        for ch in KidsChannel.objects.filter(active=True):
            try:
                n += refresh(ch)
            except Exception as e:
                self.stderr.write("kids: %s: %s" % (ch.name, e))
        self.stdout.write("kids: %d videos checked" % n)
