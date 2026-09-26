import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import ChatMessage, ChatThread

FILES_DIR = getattr(settings, "CHAT_FILES_DIR", "/var/lib/gunicorn-academy/chat_files")


class Command(BaseCommand):
    help = "Delete chat messages past their chat's disappearing time, with their photos and files."

    def handle(self, *args, **opts):
        gone = 0
        for t in ChatThread.objects.filter(disappear_hours__gt=0):
            old = ChatMessage.objects.filter(thread=t, created_at__lt=timezone.now() - timezone.timedelta(hours=t.disappear_hours))
            for img, att in old.values_list("image", "attachment"):
                for base, rel in ((settings.MEDIA_ROOT, img), (FILES_DIR, att)):
                    if rel:
                        try:
                            os.remove(os.path.join(base, rel))
                        except OSError:
                            pass
            gone += old.delete()[0]
        self.stdout.write("expired messages deleted: %d" % gone)
