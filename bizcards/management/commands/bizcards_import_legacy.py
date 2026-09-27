"""Move the old one-per-member visiting cards (vcard app) into digital business cards, keeping their old links."""
import re

from django.core.management.base import BaseCommand

from bizcards.models import Card
from bizcards.views import clean


class Command(BaseCommand):
    help = "Import old visiting cards into digital business cards (safe to run twice)."

    def handle(self, *args, **o):
        try:
            from vcard.models import VisitingCard
        except Exception:
            self.stdout.write("no old visiting cards app - nothing to do"); return
        done = 0
        for v in VisitingCard.objects.select_related("user"):
            if Card.objects.filter(legacy_token=v.token).exists():
                continue
            base = re.sub(r"[^a-z0-9]+", "-", (v.display_name or getattr(v.user, "full_name", "") or "card").lower()).strip("-")[:30] or "card"
            base = (base + "-card") if len(base) < 5 else base
            slug, i = base, 2
            while Card.objects.filter(slug=slug).exists():
                slug = "%s-%d" % (base, i); i += 1
            connect = []
            if v.phone and v.show_phone: connect.append({"type": "mobile", "value": v.phone})
            if v.whatsapp and v.show_whatsapp: connect.append({"type": "whatsapp", "value": v.whatsapp})
            if getattr(v.user, "email", "") and v.show_email: connect.append({"type": "email", "value": v.user.email})
            if v.website: connect.append({"type": "website", "value": v.website})
            social = [{"label": n.title(), "net": n, "url": getattr(v, n)} for n in ("linkedin", "instagram", "twitter") if getattr(v, n, "")]
            data = clean({"profile": {"name": v.display_name, "heading": v.role, "sub": v.org},
                          "connect": connect,
                          "sections": ([{"type": "contact", "title": "Contact", "address": v.city}] if v.city else []) + ([{"type": "social", "title": "Follow me", "items": social}] if social else []),
                          "design": {"template": "classic"}})
            Card.objects.create(owner=v.user, slug=slug, data=data, legacy_token=v.token, active=v.is_public)
            done += 1
            self.stdout.write("  moved: /card/%s -> /c/%s" % (v.token, slug))
        self.stdout.write("old cards moved: %d" % done)
