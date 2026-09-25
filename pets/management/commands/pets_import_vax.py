"""Import vaccine templates from a PenFlow dumpdata file (petcare.VaccinationTemplate)."""
import json

from django.core.management.base import BaseCommand, CommandError

from pets.models import SPECIES, VaccineTemplate


class Command(BaseCommand):
    help = "Import vaccine templates from a PenFlow JSON dump."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **opts):
        try:
            rows = json.load(open(opts["path"], encoding="utf-8"))
        except Exception as e:
            raise CommandError("Could not read %s: %s" % (opts["path"], e))
        ok = dict(SPECIES)
        made = skipped = 0
        for row in rows:
            f = row.get("fields", {})
            sp = f.get("species")
            if sp not in ok or not f.get("vaccine_name"):
                skipped += 1
                continue
            _, created = VaccineTemplate.objects.get_or_create(
                species=sp, vaccine_name=f["vaccine_name"], due_at_weeks=int(f.get("due_at_weeks") or 0),
                defaults={"repeat_every_days": f.get("repeat_every_days"), "notes": (f.get("notes") or "")[:300]})
            made += int(created)
            skipped += int(not created)
        self.stdout.write("templates added: %d, skipped: %d" % (made, skipped))
