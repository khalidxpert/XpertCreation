from django.core.management.base import BaseCommand

from notifications.groupbot import run_timers


class Command(BaseCommand):
    help = "Post the group bots' timed messages that are due."

    def handle(self, *args, **opts):
        self.stdout.write("timed bot messages posted: %d" % run_timers())
