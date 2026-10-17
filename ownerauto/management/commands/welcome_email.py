"""python manage.py welcome_email --test you@example.com      send a sample to yourself
   python manage.py welcome_email --accept                     owner: accept all waiting requests now and follow them back"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    def add_arguments(self, p):
        p.add_argument("--test", default="")
        p.add_argument("--accept", action="store_true")

    def handle(self, *a, **o):
        from ownerauto.signals import OWNER, _follow
        from ownerauto.welcome import send_welcome
        User = get_user_model()
        owner = User.objects.filter(username__iexact=OWNER).first()
        if o["test"]:
            print("sent:", send_welcome(owner or User.objects.order_by("id").first(), to=o["test"]))
        if o["accept"] and owner:
            from network.models import Connection, Follow
            n = 0
            for c in Connection.objects.filter(to_user=owner, state=Connection.PENDING):
                Connection.objects.filter(pk=c.pk).update(state=Connection.ACCEPTED, responded_at=timezone.now()); _follow(owner.pk, c.from_user_id); n += 1
            m = 0
            for f in Follow.objects.filter(following=owner).exclude(follower=owner):
                if not Follow.objects.filter(follower=owner, following_id=f.follower_id).exists():
                    _follow(owner.pk, f.follower_id); m += 1
            print("accepted requests:", n, "| followed back:", m)
