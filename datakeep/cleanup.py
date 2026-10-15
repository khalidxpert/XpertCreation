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
