"""Change one member's rewards balance by hand (for testing, or to correct a mistake). Logged in the balance.
  manage.py rewards_adjust khalidxpert 200 "Test money"
  manage.py rewards_adjust khalidxpert -200 "Test money removed"
Adjustments are never counted as prizes, so they do not use the campaign budget or show on the winners list."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from rewards.models import RewardEntry
from rewards.views import balance


class Command(BaseCommand):
    help = "Add or remove rupees from a member's rewards balance: username amount note"

    def add_arguments(self, p):
        p.add_argument("username")
        p.add_argument("amount", type=int)
        p.add_argument("note")

    def handle(self, *args, **o):
        u = get_user_model().objects.filter(username__iexact=o["username"]).first()
        if not u:
            raise CommandError("No member with that username.")
        if o["amount"] == 0 or abs(o["amount"]) > 100000:
            raise CommandError("Amount must be between -100000 and 100000, not 0.")
        if balance(u) + o["amount"] < 0:
            raise CommandError("That would make the balance negative (now Rs %d)." % balance(u))
        RewardEntry.objects.create(user=u, amount=o["amount"], kind="adjust", note=o["note"][:200])
        self.stdout.write("%s balance is now Rs %d" % (u.username, balance(u)))
