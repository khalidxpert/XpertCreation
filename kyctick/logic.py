import logging

from django.utils import timezone

log = logging.getLogger("kyctick")


def _profile(u):
    try:
        from network.models import ProProfile
        return ProProfile.objects.filter(user=u).first()
    except Exception:
        return None


def kyc_ok(u):
    try:
        from companies.models import PersonKyc
        return PersonKyc.objects.filter(user_id=u.pk, status="approved").exists()      # fresh from the database
    except Exception:
        return False


def tick_paid(u):
    try:
        from shop.models import Order
        return Order.objects.filter(user=u, product="blue_tick", status="paid").exists()
    except Exception:
        return False


def _notify(u, text, link):
    try:
        from notifications.views import notify
        notify(u, "kyc", text, link)
    except Exception:
        pass


def _set(p, on):
    upd = {"verified": on}
    if "verified_at" in {f.name for f in p._meta.get_fields()}:
        upd["verified_at"] = timezone.now() if on else None
    type(p).objects.filter(pk=p.pk).update(**upd)


def sync(u, why=""):
    """Switch the blue tick on when it is paid AND the ID is approved."""
    p = _profile(u)
    if not p or p.verified:
        return
    if tick_paid(u) and kyc_ok(u):
        _set(p, True)
        _notify(u, "✔ Your blue tick is on. Thank you!", "/in/" + p.slug)
        log.warning("blue tick on for user %s (%s)", u.pk, why)


def on_order(sender, instance, created=False, **kw):
    o = instance
    if o.product != "blue_tick":
        return
    u = o.user
    if o.status == "paid":
        if kyc_ok(u):
            sync(u, "paid")
        elif not getattr(o, "_kyctick_told", False):
            o._kyctick_told = True
            _notify(u, "Blue tick paid ✔ Now send your ID for the check, then the tick switches on.", "/get-verified")
    elif o.status == "refunded" and not tick_paid(u):
        p = _profile(u)
        if p and p.verified:
            _set(p, False)
            log.warning("blue tick off for user %s (refunded)", u.pk)


def on_kyc(sender, instance, created=False, **kw):
    k = instance
    if k.status == "approved":
        sync(k.user, "kyc approved")
    elif k.status == "rejected" and tick_paid(k.user):
        try:
            from notifications.views import notify_admins
            notify_admins("payment", "ID check rejected for %s, who paid for the blue tick. Refund the Blue tick order." % (k.user.email,), "/payments-admin")
        except Exception:
            pass
