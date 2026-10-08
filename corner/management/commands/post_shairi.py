"""Urdu Shairi channel: creates the channel once (owner, listed in the groups directory), then each run posts the
next couplet through the group bot. Usage: manage.py post_shairi [--setup-only] [--owner EMAIL]"""
import json
import os
import random
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from corner.content import POETRY

DESC = "Classic Urdu poetry: a couplet every two hours (9 am to 11 pm) from Ghalib, Mir, Iqbal and more, with simple meanings. By XpertCreation."


class Command(BaseCommand):
    help = "Post the next Urdu couplet to the Urdu Shairi channel (creates the channel the first time)."

    def add_arguments(self, p):
        p.add_argument("--owner", default="khalid@xpertcreation.com")
        p.add_argument("--setup-only", action="store_true")

    def handle(self, *a, **o):
        from notifications.models import ChatGroup, GroupMember, GroupMessage
        path = os.path.join(settings.MEDIA_ROOT, "shairi.json")
        st = json.load(open(path)) if os.path.exists(path) else {}
        save = lambda: (os.makedirs(os.path.dirname(path), exist_ok=True), json.dump(st, open(path, "w")))
        g = ChatGroup.objects.filter(pk=st.get("group")).first() if st.get("group") else None
        if not g:
            owner = get_user_model().objects.filter(email__iexact=o["owner"]).first()
            g = ChatGroup.objects.create(name="\U0001F4D6 Urdu Shairi", description=DESC, created_by=owner, only_admins_send=True, invite_code=secrets.token_hex(5))
            roles = [c[0] for c in (GroupMember._meta.get_field("role").choices or [])]
            role = "owner" if "owner" in roles else ("admin" if "admin" in roles else "member")
            if owner:
                GroupMember.objects.get_or_create(group=g, user=owner, defaults={"role": role})
            try:
                from groupdir.models import Listing
                Listing.objects.update_or_create(group=g, defaults={"listed": True})
            except Exception:
                pass
            st = {"group": g.id, "next": 0}
            save()
            self.stdout.write("shairi: channel created (id %d, invite /group/join/%s)" % (g.id, g.invite_code))
        # Quiet channel: mute everyone once (new members too); someone who unmutes later keeps that choice.
        try:
            done = set(st.get("muted", []))
            new = list(GroupMember.objects.filter(group=g).exclude(user_id__in=done).values_list("user_id", flat=True))
            if new:
                GroupMember.objects.filter(group=g, user_id__in=new).update(muted=True)
                st["muted"] = sorted(done | set(new)); save()
        except Exception:
            pass
        if o["setup_only"]:
            return
        order = list(range(len(POETRY)))
        random.Random(786).shuffle(order)
        i = st.get("next", 0) % len(order)
        p = POETRY[order[i]]
        text = "\U0001F4D6 %s\n\n\u2014 %s\n\n%s\n%s\n\nxpertcreation.com/poetry" % (p[1], p[0], p[2], p[3])
        # also post this couplet to IRC #shairi (ShairiBot picks it up)
        try:
            import time as _t
            open("/var/lib/xc-ircbot/queue/%d.txt" % int(_t.time() * 1000), "w", encoding="utf-8").write(text)
        except Exception:
            pass
        try:
            from notifications.groupbot import say
            say(g, text[:2000])
        except ImportError:
            GroupMessage.objects.create(group=g, body=text[:2000])
        ChatGroup.objects.filter(pk=g.pk).update(updated_at=timezone.now())
        st["next"] = i + 1
        save()
        self.stdout.write("shairi: posted %d of %d (%s)" % (i + 1, len(order), p[0]))
