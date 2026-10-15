"""Block / mute / restrict / close friends - used by the feed, profiles and comments (hooks added by setup_social_v3)."""
from django.db.models import Q


def blocked_ids(u):
    """People blocked by u or who blocked u (blocking works both ways). Same list as chat blocking."""
    if not u or not u.is_authenticated:
        return set()
    try:
        from notifications.models import ChatBlock
        rows = ChatBlock.objects.filter(Q(blocker=u) | Q(blocked=u)).values_list("blocker_id", "blocked_id")
        return {b if a == u.pk else a for a, b in rows}
    except Exception:
        return set()


def blocked_between(a_id, b_id):
    try:
        from notifications.models import ChatBlock
        return ChatBlock.objects.filter(Q(blocker_id=a_id, blocked_id=b_id) | Q(blocker_id=b_id, blocked_id=a_id)).exists()
    except Exception:
        return False


def muted_ids(u):
    if not u or not u.is_authenticated:
        return set()
    from .models import Mute
    return set(Mute.objects.filter(user=u).values_list("target_id", flat=True))


def close_authors(u):
    """Authors who put u on their Close friends list."""
    if not u or not u.is_authenticated:
        return set()
    from .models import CloseFriend
    return set(CloseFriend.objects.filter(friend=u).values_list("owner_id", flat=True))


def in_close(owner_id, friend_id):
    from .models import CloseFriend
    return CloseFriend.objects.filter(owner_id=owner_id, friend_id=friend_id).exists()


def restricted_by(owner_id):
    from .models import Restrict
    return set(Restrict.objects.filter(user_id=owner_id).values_list("target_id", flat=True))


def comment_filter(qs, post, u):
    """Comments by people the post's author restricted: only they and the author see them."""
    r = restricted_by(post.author_id)
    if not r:
        return qs
    viewer = u.pk if u.is_authenticated else None
    if viewer == post.author_id:
        return qs
    return qs.exclude(Q(author_id__in=r) & ~Q(author_id=viewer))
