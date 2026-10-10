from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Freelance clock: deadline reminders, late orders, auto-accept, cancel requests, offer expiry, unpaid orders."

    def handle(self, *args, **options):
        from market.views import tick
        self.stdout.write("market_tick: %s" % tick())
