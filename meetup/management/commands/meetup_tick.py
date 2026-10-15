from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Meetup reminders (a day before). Run every 15 minutes from cron."

    def handle(self, *a, **k):
        from meetup.views import tick
        n = tick()
        if n:
            self.stdout.write("meetup reminders sent: %d" % n)
