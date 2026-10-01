import os
import secrets
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from companies.models import Company


class Command(BaseCommand):
    help = "Create the XpertCreation company page (verified, owned by Khalid). Safe to run twice."

    def handle(self, *args, **o):
        if Company.objects.filter(slug="xpertcreation").exists():
            self.stdout.write("XpertCreation page already exists"); return
        k = get_user_model().objects.filter(email="khalid@xpertcreation.com").order_by("id").first()
        if not k:
            self.stdout.write("khalid@xpertcreation.com not found"); return
        c = Company.objects.create(
            owner=k, name="XpertCreation", slug="xpertcreation",
            tagline="Learn more. Do more. All in one place.",
            about=("XpertCreation is a free, all-in-one platform made in Lahore, Pakistan: free courses, 78 tools, jobs, "
                   "XpertConnect, chat, pets, sports, shows and games - one free account for everything."),
            industry="Technology & Education", size="1-10", city="Lahore", country="PK",
            address="1-S-3B/2, Ghazali Park, Wahdat Colony, Lahore 54000, Pakistan",
            website="https://xpertcreation.com", email="khalid@xpertcreation.com", phone="+923009462916", whatsapp="+923009462916",
            status=Company.APPROVED, review_note="Platform owner", reviewed_by=k, reviewed_at=timezone.now(),
            domain="xpertcreation.com", domain_token=secrets.token_hex(16), domain_verified_at=timezone.now())
        src = next((p for p in ("/var/www/xpertcreation-landing/brand/icon-512.png", "/var/www/xpertcreation-landing/brand/logo-64.png") if os.path.exists(p)), None)
        if src:
            from PIL import Image
            rel = "companies/%d/logo-%s.webp" % (c.id, secrets.token_hex(8))
            os.makedirs(os.path.join(settings.MEDIA_ROOT, os.path.dirname(rel)), exist_ok=True)
            Image.open(src).convert("RGBA").save(os.path.join(settings.MEDIA_ROOT, rel), "WEBP", quality=90)
            c.logo = rel; c.save(update_fields=["logo"])
        self.stdout.write("XpertCreation company page created: /company/xpertcreation (verified)")
