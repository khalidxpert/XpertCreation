import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import ChatMessage, ChatThread


class Command(BaseCommand):
    help = "Delete chat messages past their chat's disappearing time, with their photos."

    def handle(self, *args, **opts):
        gone = 0
        for t in ChatThread.objects.filter(disappear_hours__gt=0):
            old = ChatMessage.objects.filter(thread=t, created_at__lt=timezone.now() - timezone.timedelta(hours=t.disappear_hours))
            for path in old.exclude(image="").values_list("image", flat=True):
                try:
                    os.remove(os.path.join(settings.MEDIA_ROOT, path))
                except OSError:
                    pass
            gone += old.delete()[0]
        self.stdout.write("expired messages deleted: %d" % gone)
