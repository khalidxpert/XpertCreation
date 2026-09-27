from django.core.management.base import BaseCommand

from sports import feeds


class Command(BaseCommand):
    help = "Refresh sports data that is due (runs every 2 minutes; each feed decides whether it's due)."

    def add_arguments(self, p):
        p.add_argument("--force", action="store_true", help="fetch everything now")

    def handle(self, *args, **o):
        f = o["force"]
        n = feeds.refresh_cricket(f) + feeds.refresh_football(f) + feeds.refresh_other(f)
        self.stdout.write("sports requests made: %d (cricket today: %d/100)" % (n, feeds.used("cricapi")))
