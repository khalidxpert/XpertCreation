import json
import urllib.request

from django.core.management.base import BaseCommand

from rates.views import CURRENCIES, save_rate

URL = "https://open.er-api.com/v6/latest/USD"


class Command(BaseCommand):
    help = "Fetch exchange rates (PKR per unit of each currency)."

    def handle(self, *args, **o):
        req = urllib.request.Request(URL, headers={"User-Agent": "XpertCreation/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
        r = data.get("rates") or {}
        pkr = r.get("PKR")
        if data.get("result") != "success" or not pkr:
            self.stderr.write("rates: unexpected answer"); return
        n = 0
        for k, _, _ in CURRENCIES:
            c = r.get(k.upper())
            if c:
                save_rate(k, pkr / c, "open.er-api.com"); n += 1
        self.stdout.write("rates: %d currencies saved (1 USD = %.2f PKR)" % (n, pkr))
