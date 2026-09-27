import os
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand

from autopost import posting


class Command(BaseCommand):
    help = "Create the official account, make it an admin of the XpertCreation group, give the group the logo, add verified members."

    def add_arguments(self, p):
        p.add_argument("--add-existing", action="store_true", help="also add every existing verified member to the group")

    def handle(self, *args, **o):
        from notifications.models import GroupMember
        u = posting.official()
        self.stdout.write("official account: %s (id %d)" % (u.email, u.id))
        g = posting.group()
        if not g:
            self.stdout.write("group %d not found - nothing else to do" % posting.GROUP_ID); return
        m, _ = GroupMember.objects.get_or_create(group=g, user=u)
        if m.role != "admin":
            m.role = "admin"; m.save(update_fields=["role"])
        self.stdout.write("official account is admin of: %s" % g.name)
        logo = next((p for p in ("/brand/icon-512.png", "/brand/logo-512.png", "/brand/icon-192.png", "/brand/logo-192.png", "/brand/logo-64.png")
                     if os.path.exists(posting.LAND + p)), None)
        if logo and not g.photo:
            from PIL import Image
            rel = "chat/g%d/%s.webp" % (g.id, secrets.token_hex(12))
            full = os.path.join(settings.MEDIA_ROOT, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            Image.open(posting.LAND + logo).convert("RGBA").save(full, "WEBP", quality=90)
            g.photo = rel; g.save(update_fields=["photo"])
            self.stdout.write("group picture set from %s" % logo)
        av = getattr(type(u), "avatar", None)
        if logo and hasattr(u, "avatar") and not u.avatar:
            try:
                field = u._meta.get_field("avatar")
                from django.core.files import File
                if hasattr(field, "upload_to"):
                    with open(posting.LAND + logo, "rb") as fh:
                        u.avatar.save("xpertcreation-official.png", File(fh), save=True)
                    self.stdout.write("official account picture set")
            except Exception as e:
                self.stdout.write("account picture not set (%s) - you can add it from the admin" % type(e).__name__)
        if o["add_existing"]:
            from django.contrib.auth import get_user_model
            n = 0
            for x in get_user_model().objects.filter(is_active=True):
                if getattr(x, "is_email_verified", True) and posting.add_to_official_group(x, welcome=False):   # quietly: no 30 welcomes at once
                    n += 1
            self.stdout.write("existing members added: %d" % n)
