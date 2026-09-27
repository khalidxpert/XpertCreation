import os
from datetime import datetime

from django.core.management.base import BaseCommand

from autopost import posting


class Command(BaseCommand):
    help = "Write the tools catalogue (every tool, purpose, how it works, link) to /root/send/ with a timestamp."

    def handle(self, *args, **o):
        os.makedirs("/root/send", exist_ok=True)
        p = "/root/send/tools_catalogue_%s.md" % datetime.now().strftime("%Y%m%d_%H%M%S")
        open(p, "w").write(posting.catalogue_markdown())
        self.stdout.write("written %s (%d tools)" % (p, len(posting.tools())))
