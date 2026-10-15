from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Event reminders (a day before and an hour before). Run every 15 minutes from cron."

    def handle(self, *a, **k):
        from xsocial.views3 import tick
        n = tick()
        if n:
            self.stdout.write("event reminders sent: %d" % n)
