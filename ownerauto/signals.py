"""1) The owner (khalidxpert) accepts every connection request at once and follows the person back.
      Anyone who follows the owner is followed back too.
   2) Every new member gets the welcome email once, as soon as their email is verified."""
import logging
import threading

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

OWNER = "khalidxpert"
log = logging.getLogger(__name__)
User = get_user_model()


def _owner_id():
    from django.core.cache import cache
    oid = cache.get("oa:owner")
    if oid is None:
        oid = User.objects.filter(username__iexact=OWNER).values_list("pk", flat=True).first() or 0
        cache.set("oa:owner", oid, 3600)
    return oid


def _follow(a, b):
    try:
        from network.models import Follow
        if a and b and a != b:
            Follow.objects.get_or_create(follower_id=a, following_id=b)
    except Exception:
        log.exception("owner auto follow")


try:
    from network.models import Connection, Follow

    @receiver(post_save, sender=Connection, dispatch_uid="ownerauto_conn")
    def owner_accepts(sender, instance, **kw):
        oid = _owner_id()
        if not oid or instance.to_user_id != oid or instance.state != Connection.PENDING:
            return
        Connection.objects.filter(pk=instance.pk, state=Connection.PENDING).update(state=Connection.ACCEPTED, responded_at=timezone.now())
        _follow(oid, instance.from_user_id)
        try:
            from notifications.views import notify
            notify(instance.from_user, "connect", "Syed Khalid Hussain Shah (XpertCreation CEO) accepted your connection request \U0001F91D", "/in/" + OWNER)
        except Exception:
            pass

    @receiver(post_save, sender=Follow, dispatch_uid="ownerauto_follow")
    def owner_follows_back(sender, instance, created, **kw):
        oid = _owner_id()
        if created and oid and instance.following_id == oid and instance.follower_id != oid:
            _follow(oid, instance.follower_id)
except Exception:
    log.exception("ownerauto: network app not found")


@receiver(pre_save, sender=User, dispatch_uid="ownerauto_pre")
def remember_verified(sender, instance, **kw):
    if instance.pk:
        instance._oa_was = User.objects.filter(pk=instance.pk).values_list("is_email_verified", flat=True).first()


@receiver(post_save, sender=User, dispatch_uid="ownerauto_post")
def welcome_when_verified(sender, instance, created, **kw):
    if not getattr(instance, "is_email_verified", False) or not instance.email:
        return
    if not created and getattr(instance, "_oa_was", True):
        return                                   # it was already verified before this save
    from .models import WelcomeSent
    from .welcome import send_welcome
    if WelcomeSent.objects.filter(user=instance).exists():
        return
    WelcomeSent.objects.get_or_create(user=instance)
    threading.Thread(target=send_welcome, args=(instance,), daemon=True).start()
