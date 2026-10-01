from django.core.management.base import BaseCommand

from accounts.models import User
from accounts.usernames import suggest


class Command(BaseCommand):
    help = "Give every member without a username one made from their name (they can change it in Settings)."

    def handle(self, *args, **o):
        n = 0
        for u in User.objects.filter(username__isnull=True).order_by("id"):
            name = suggest(u.full_name or u.email.split("@")[0], u)
            if name:
                User.objects.filter(pk=u.pk).update(username=name); n += 1
        self.stdout.write("usernames given: %d" % n)
