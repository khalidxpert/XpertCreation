from django.core.management.base import BaseCommand
from django.utils import timezone

from stories.models import Story
from stories.views import _remove


class Command(BaseCommand):
    help = "Delete stories (and their photos) older than 24 hours."

    def handle(self, *args, **o):
        n = 0
        for s in Story.objects.filter(expires_at__lte=timezone.now()):
            _remove(s); n += 1
        self.stdout.write("stories removed: %d" % n)
