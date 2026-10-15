"""What must be finished before a member can delete their account (so nobody loses money or an order in the middle)."""
from django.db.models import Q, Sum


def blockers(u):
    out = []
    try:
        from market.models import Entry, Order, Payout
        n = Order.objects.filter(Q(buyer=u) | Q(seller=u), status__in=("active", "delivered", "disputed", "refund_due")).count()
        if n:
            out.append("You have %d freelance order%s in progress (finish or cancel %s on /market#orders)." % (n, "" if n == 1 else "s", "it" if n == 1 else "them"))
        if Payout.objects.filter(user=u, status="requested").exists():
            out.append("A withdrawal of your earnings is still being sent.")
        bal = Entry.objects.filter(user=u).aggregate(s=Sum("amount"))["s"] or 0
        if bal > 0:
            out.append("You still have Rs %s in freelance earnings - withdraw it first on /market#wallet." % "{:,}".format(bal))
    except Exception:
        pass
    try:
        from store.models import Order as SO
        n = SO.objects.filter(Q(buyer=u) | Q(merchant__user=u), status__in=("placed", "confirmed", "shipped", "delivered", "disputed", "refund_due")).count()
        if n:
            out.append("You have %d Store order%s that %s not finished yet." % (n, "" if n == 1 else "s", "is" if n == 1 else "are"))
    except Exception:
        pass
    try:
        from payproof.models import PayProof
        if PayProof.objects.filter(user=u, status="pending").exists():
            out.append("A JazzCash payment you sent is still being checked by our team.")
    except Exception:
        pass
    return out
