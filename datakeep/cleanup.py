"""When an account is deleted: remove the member's uploaded files from the server (documents, payment screenshots,
receipts, photos, chat files) and keep an anonymous copy of their payment records."""
import logging
import os
import re
import shutil

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q

log = logging.getLogger("datakeep")
PATH = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9_\-./]{3,200}\.(jpe?g|png|webp|gif|heic|heif|pdf|mp4|webm|mov|m4a|ogg|opus|mp3|aac|wav|bin|docx?|xlsx?|pptx?|zip|txt|csv)$", re.I)
SKIP_MEDIA = {"brand", "quran", "seo", "geo", "static", "autopost", "shairi.json"}


def _roots():
    base = "/var/lib/gunicorn-academy"
    r = [("media", str(settings.MEDIA_ROOT))]
    for env, d in (("XC_PAYPROOF_DIR", base + "/payproofs"), ("XC_KYC_DIR", base + "/kyc_docs"),
                   ("XC_RIDES_DOCS", base + "/kyc_docs/rides"), ("XC_MARKET_FILES", base + "/market_files")):
        r.append(("private", os.environ.get(env, d)))
    r.append(("private", getattr(settings, "CHAT_FILES_DIR", base + "/chat_files")))
    return [(k, os.path.realpath(p)) for k, p in r if p]


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _strings(x)


def _values(o):
    for f in o._meta.concrete_fields:
        if isinstance(f, (models.FileField, models.CharField, models.JSONField)):
            try:
                v = getattr(o, f.attname)
            except Exception:
                continue
            if isinstance(f, models.FileField):
                v = getattr(v, "name", "") or ""
            yield from _strings(v)


def _files_for(objs, roots):
    found = set()
    for o in objs:
        for s in _values(o):
            s = s.strip()
            if not s or not PATH.match(s):
                continue
            s = s.split("/media/", 1)[-1].lstrip("/") if s.startswith("/media/") else s
            for kind, root in roots:
                if kind == "media" and s.split("/", 1)[0] in SKIP_MEDIA:
                    continue
                full = os.path.realpath(os.path.join(root, s))
                if full.startswith(root + os.sep) and os.path.isfile(full):
                    found.add(full)
    return found


def _keep(user):
    from .models import KeptRecord

    def put(**k):
        try:
            KeptRecord.objects.get_or_create(kind=k.pop("kind"), no=k.pop("no"), defaults=k)
        except Exception:
            log.exception("keep record")
    try:
        from shop.models import Order
        for o in Order.objects.filter(user=user, status__in=("paid", "refunded")):
            put(kind="promote", no="P-%d" % o.id, role="buyer", item=("%s %s" % (o.product, o.plan))[:160], amount=o.amount, fee=o.amount,
                status=o.status, provider=o.provider, provider_ref=o.provider_ref, paid_at=o.paid_at)
    except Exception:
        log.exception("keep promote")
    try:
        from market.models import Order, Payout
        for o in Order.objects.filter(Q(buyer=user) | Q(seller=user), paid_at__isnull=False):
            put(kind="freelance", no="XM-%06d" % o.id, role="buyer" if o.buyer_id == user.pk else "seller", item=o.title[:160], amount=o.amount,
                fee=o.fee, status=o.status, provider=o.provider, provider_ref=o.provider_ref, paid_at=o.paid_at)
        for p in Payout.objects.filter(user=user, status="paid"):
            put(kind="payout", no="WD-%d" % p.id, role="seller", item=p.method, amount=p.amount, status=p.status, provider=p.method,
                provider_ref=p.reference, paid_at=p.done_at)
    except Exception:
        log.exception("keep freelance")
    try:
        from store.models import Order
        for o in Order.objects.filter(Q(buyer=user) | Q(merchant__user=user)).filter(Q(paid_at__isnull=False) | Q(status="completed")):
            put(kind="store", no="XS-%06d" % o.id, role="buyer" if o.buyer_id == user.pk else "seller", item=("%d item(s)" % len(o.items or []))[:160],
                amount=o.total, fee=o.fee, status=o.status, provider=o.provider or o.payment, provider_ref=o.provider_ref, paid_at=o.paid_at)
    except Exception:
        log.exception("keep store")


def on_user_delete(sender, instance, using=None, **kw):
    user = instance
    _keep(user)
    files, dirs = set(), []
    try:
        from django.db.models.deletion import Collector
        c = Collector(using=using or "default")
        c.collect([user])
        roots = _roots()
        objs = [o for model, items in c.data.items() if model is not sender for o in items]
        for qs in c.fast_deletes:
            try:
                objs.extend(qs[:20000])
            except Exception:
                pass
        files = _files_for(objs, roots)
        money = os.path.join(os.environ.get("XC_MONEY_FILES", "/var/lib/gunicorn-academy/money_files"), str(user.pk))
        if os.path.isdir(money):
            dirs.append(money)
    except Exception:
        log.exception("collect files")
    avatar = getattr(user, "avatar", "") or ""

    def remove():
        n = 0
        for f in files:
            try:
                os.remove(f); n += 1
            except OSError:
                pass
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
        if avatar:
            try:
                from accounts.views import _drop_avatar_file
                _drop_avatar_file(avatar)
            except Exception:
                pass
        log.warning("Account %s deleted: %d files and %d folders removed", user.pk, n, len(dirs))
    transaction.on_commit(remove, using=using or "default")


# ---- keep the other side's order history (setup_secure_v1) ----
def placeholder(tag=""):
    """A locked 'Deleted member' account that keeps finished orders for the other side (no email, no password, can't sign in)."""
    from django.contrib.auth import get_user_model
    U = get_user_model()
    email = "deleted-member%s@xpertcreation.invalid" % (("-" + tag) if tag else "")
    u = U.objects.filter(email=email).first()
    if u:
        return u
    fields = {f.name for f in U._meta.get_fields()}
    kw = {}
    if "full_name" in fields:
        kw["full_name"] = "Deleted member"
    if "username" in fields:
        kw["username"] = ("deleted-" + (tag or "member"))[:20]
    u = U(email=email, **kw) if "email" in fields else U(**kw)
    u.set_unusable_password()
    u.is_active = False
    u.save()
    return u


def handover(user):
    """Before an account is deleted: finished Freelance and Store orders stay for the seller / buyer, under 'Deleted member'.
    The deleted person's name, phone and address are wiped from those orders."""
    ph = None
    try:
        from market.models import Order as MO
        q1 = MO.objects.filter(buyer=user).exclude(status="pending")
        q2 = MO.objects.filter(seller=user).exclude(status="pending")
        if q1.exists() or q2.exists():
            ph = ph or placeholder()
            q1.update(buyer=ph)
            q2.update(seller=ph)
    except Exception:
        log.exception("handover freelance")
    try:
        from store.models import Order as SO, Review as SR, Merchant, Product
        q = SO.objects.filter(buyer=user).exclude(status="pending")
        if q.exists():
            ph = ph or placeholder()
            q.update(buyer=ph, name="Deleted member", phone="", address="", note="")
            SR.objects.filter(buyer=user).update(buyer=ph)
        m = Merchant.objects.filter(user=user).first()
        if m and SO.objects.filter(merchant=m).exclude(status="pending").exists():
            Product.objects.filter(merchant=m).update(active=False)            # the shop closes, its orders stay for the buyers
            Merchant.objects.filter(pk=m.pk).update(user=placeholder("shop-%d" % m.pk), status="suspended", phone="", address="",
                                                    note="Owner deleted their account")
    except Exception:
        log.exception("handover store")
