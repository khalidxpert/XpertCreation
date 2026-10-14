"""Every 15 minutes: the XpertCreation account (@khalidxpert) announces new approved shops, new services and new
property listings on XpertConnect and in the XpertCreation group, tagging the owner (@username) with hashtags.
At most 2 posts a run, so the feed is never flooded. Only items from the last 7 days; each one is posted once."""
import re
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from brandkit.models import PromoPost

SITE = "https://xpertcreation.com"
PER_RUN = 2


def _tag(s):
    w = re.findall(r"[A-Za-z0-9]+", s or "")
    t = "".join(x[:1].upper() + x[1:] for x in w)[:28]
    return "#" + t if t else ""


def _who(u):
    un = getattr(u, "username", "") or ""
    return "@" + un if un else ((getattr(u, "full_name", "") or "a new member").strip())


def _tags(*xs):
    out = []
    for x in xs:
        if x and x not in out:
            out.append(x)
    return " ".join(out)


class Command(BaseCommand):
    help = "Announce new shops, services and properties from the XpertCreation account"

    def handle(self, *a, **k):
        from autopost.posting import _publish
        now = timezone.now()
        since = now - timedelta(days=7)
        jobs = []
        try:
            from store.models import Merchant
            for m in Merchant.objects.filter(status="approved", created_at__gte=since - timedelta(days=23)).select_related("user").order_by("id"):
                jobs.append(("shop", m))
        except Exception:
            pass
        try:
            from market.models import CATS, Gig
            cats = dict(CATS)
            for g in Gig.objects.filter(active=True, hidden=False, created_at__gte=since, created_at__lte=now - timedelta(minutes=20)).select_related("seller").order_by("id"):
                jobs.append(("gig", g))
        except Exception:
            cats = {}
        try:
            from realestate.models import Listing
            for l in Listing.objects.filter(status="active", hidden=False, created_at__gte=since, created_at__lte=now - timedelta(minutes=20)).select_related("owner").order_by("id"):
                jobs.append(("property", l))
        except Exception:
            pass
        done = set(PromoPost.objects.values_list("kind", "ref"))
        sent = 0
        for kind, o in jobs:
            if sent >= PER_RUN:
                break
            if (kind, o.id) in done:
                continue
            if kind == "shop":
                text = ("\U0001F6CD️ New on the XpertCreation Store!\n\n%s by %s is now open%s.%s\n\nVisit the shop: %s/shop/%s\n\n%s"
                        % (o.name, _who(o.user), (" in " + o.city) if o.city else "", ("\n" + o.about[:220]) if o.about else "", SITE, o.slug,
                           _tags("#XpertCreation", "#XpertStore", "#OnlineShopping", _tag(o.name), _tag(o.city), "#ShopLocal", "#Pakistan")))
                imgs = [o.logo] if o.logo else []
            elif kind == "gig":
                cat = cats.get(o.category, "")
                text = ("\U0001F4BC New service on XpertFreelance\n\n“%s” by %s\nFrom Rs %s · delivery in %s day%s\n\nOrder safely (the seller is paid when you accept the work): %s/market#gig-%d\n\n%s"
                        % (o.title, _who(o.seller), "{:,}".format(o.price), o.days, "" if o.days == 1 else "s", SITE, o.id,
                           _tags("#XpertCreation", "#XpertFreelance", "#Freelance", _tag(cat.split(" ")[0] if cat else ""), "#HireOnXpertCreation", "#Pakistan")))
                imgs = list(o.images or [])[:1]
            else:
                text = ("\U0001F3E0 New property on XpertCreation\n\n%s\n%s · Rs %s · posted by %s\n\nSee details and contact the owner: %s/market#prop-%d\n\n%s"
                        % (o.title, o.city, "{:,}".format(o.price), _who(o.owner), SITE, o.id,
                           _tags("#XpertCreation", "#Property", "#RealEstate", "#ForSale" if o.purpose == "sale" else "#ForRent", _tag(o.city), "#Pakistan")))
                imgs = list(o.images or [])[:1]
            try:
                p = _publish("promo_" + kind, str(o.id), text, images=imgs)
            except Exception as e:
                self.stdout.write("skip %s %s: %s" % (kind, o.id, e))
                p = None
            PromoPost.objects.get_or_create(kind=kind, ref=o.id)
            if p:
                sent += 1
                try:
                    from notifications.views import notify
                    owner = getattr(o, "user", None) or getattr(o, "seller", None) or getattr(o, "owner", None)
                    if owner and not getattr(owner, "username", ""):   # members with a username already get the @mention notification
                        notify(owner, "promo", "XpertCreation shared your new %s on XpertConnect. Share it with your friends too!" % {"shop": "shop", "gig": "service", "property": "property"}[kind], "/post/%d" % p.id)
                except Exception:
                    pass
        self.stdout.write("%s brand_promo: %d posted" % (now.strftime("%Y-%m-%d %H:%M"), sent))
