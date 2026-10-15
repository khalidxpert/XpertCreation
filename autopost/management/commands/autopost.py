from django.core.management.base import BaseCommand

from autopost import posting


class Command(BaseCommand):
    help = "Post one item from the official account: tool, drama, news or sports."

    def add_arguments(self, p):
        p.add_argument("kind", choices=["tool", "drama", "news", "sports", "guide"])

    def handle(self, *args, **o):
        fn = {"tool": posting.post_tool, "drama": posting.post_drama, "news": posting.post_news, "sports": posting.post_sports, "guide": __import__("autopost.guides", fromlist=["post_guide"]).post_guide}[o["kind"]]
        p = fn()
        self.stdout.write("%s: %s" % (o["kind"], ("posted #%d" % p.id) if p else "nothing new to post"))
