"""@username in a new post or comment notifies that member - only if they can see the post."""
import re

MENTION = re.compile(r"(?:^|[\s(])@([A-Za-z0-9_]{3,20})\b")
MAX = 10


def _notify_mentions(body, author, post, what):
    names = {n.lower() for n in MENTION.findall(body or "")}
    if not names:
        return
    from django.contrib.auth import get_user_model
    from feed.views import _can_see
    from network.views import _name
    from notifications.views import notify
    U = get_user_model()
    users = list(U.objects.filter(username__in=list(names)[:MAX], is_active=True))
    for u in users:
        if u.pk == author.pk:
            continue
        try:
            if _can_see(post, u):
                notify(u, "mention", "%s mentioned you in a %s." % (_name(author), what), "/post/%d" % post.id)
        except Exception:
            pass
    left = names - {(u.username or "").lower() for u in users}
    try:
        from companies.models import Company
        for c in Company.objects.filter(slug__in=[n.replace("_", "-") for n in list(left)[:MAX]], hidden=False).select_related("owner"):
            if c.owner_id != author.pk and _can_see(post, c.owner):
                notify(c.owner, "mention", "%s mentioned %s in a %s." % (_name(author), c.name, what), "/post/%d" % post.id)
    except Exception:
        pass


def on_post(sender, instance, created, **kw):
    if created and not instance.hidden:
        _notify_mentions(instance.body, instance.author, instance, "post")


def on_comment(sender, instance, created, **kw):
    if created and not instance.hidden:
        _notify_mentions(instance.body, instance.author, instance.post, "comment")
