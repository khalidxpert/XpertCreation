"""Rewards stage 1: points for real use of every part of the site, and a transparent leaderboard.

Points are counted from what members already do (posts, lessons, MCQs, games, typing) by the
rewards_collect job every 5 minutes, plus a small heartbeat from the page for active time, tools and reading.
Every rule has a daily cap so nobody can farm points."""
from datetime import timedelta

from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Campaign, DailyActivity, PointEvent

# kind: (app.Model, user field, time field, filters, points, max per day, section)
SOURCES = {
    "post":     ("feed.Post", "author_id", "created_at", {"hidden": False}, 5, 2, "social"),
    "comment":  ("feed.Comment", "author_id", "created_at", {"hidden": False}, 1, 5, "social"),
    "reaction": ("feed.Reaction", "user_id", "created_at", {}, 1, 5, "social"),
    "lesson":   ("academy.LessonProgress", "user_id", "completed_at", {}, 5, 6, "academy"),
    "quiz":     ("academy.Attempt", "user_id", "submitted_at", {"passed": True}, 10, 2, "academy"),
    "mcq":      ("mcq.Attempt", "user_id", "created_at", {}, 5, 1, "mcq"),
    "game":     ("games.Score", "user_id", "created_at", {}, 2, 5, "games"),
    "typing":   ("typingtutor.Score", "user_id", "created_at", {}, 2, 5, "typing"),
}
REVOKE = ("post", "comment", "reaction")       # points go away if the post is hidden or deleted
BEAT_KINDS = {"tool": (1, 5, "tools"), "read": (2, 3, "reading")}   # points, max per day, section
TIME_STEP, TIME_POINTS, TIME_CAP = 600, 2, 12  # 2 points per 10 active minutes, up to 12 a day
MAX_ACTIVE = 4 * 3600                          # active time stops counting after 4 hours a day
BEAT_EVERY = 60
SECTION = dict({k: v[6] for k, v in SOURCES.items()}, tool="tools", read="reading", time="time")


def campaign():
    c = Campaign.objects.first()
    return c or Campaign.objects.create()


def live(c=None):
    c = c or campaign()
    now = timezone.now()
    return bool(c.enabled and c.starts_at and c.ends_at and c.starts_at <= now < c.ends_at)


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def counts_for(u, c=None):
    """Live campaign: every active member. Otherwise only staff (for testing)."""
    if not u or not u.is_authenticated or getattr(u, "is_blocked", False):
        return False
    return live(c) or _staff(u)


def award(user_id, day, kind, ref, points, cap):
    """Add one point event unless it is already there or the daily cap for this kind is reached."""
    if PointEvent.objects.filter(user_id=user_id, day=day, kind=kind).count() >= cap:
        return False
    try:
        _, made = PointEvent.objects.get_or_create(user_id=user_id, kind=kind, ref=ref[:100],
                                                   defaults={"day": day, "points": points})
        return made
    except IntegrityError:
        return False


def _status(c):
    return {"on": live(c), "enabled": c.enabled, "budget": c.budget,
            "starts": c.starts_at.isoformat() if c.starts_at else "", "ends": c.ends_at.isoformat() if c.ends_at else ""}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def beat(request):
    """Sent by the page once a minute while the tab is visible and used. Adds active time,
    and points for using a tool or reading (s = "tool:<name>" or "read:<path>")."""
    u, c = request.user, campaign()
    if not counts_for(u, c):
        return Response({"on": False}, status=404)
    if not cache.add("rw:beat:%d" % u.pk, 1, BEAT_EVERY - 5):
        return Response({"ok": False, "why": "too soon"})
    day = timezone.localdate()
    row, _ = DailyActivity.objects.get_or_create(user=u, day=day)
    if row.active_seconds < MAX_ACTIVE:
        DailyActivity.objects.filter(pk=row.pk).update(active_seconds=F("active_seconds") + BEAT_EVERY)
    s = str(request.data.get("s") or "").strip()[:80]
    kind = s.split(":", 1)[0]
    if kind in BEAT_KINDS and len(s) > len(kind) + 1:
        pts, cap, _sec = BEAT_KINDS[kind]
        award(u.pk, day, kind, "%s|%s" % (s, day.isoformat()), pts, cap)
    return Response({"ok": True})


def _label(u):
    if getattr(u, "hide_from_leaderboard", False) or not u.username:
        return "Member #%d" % u.pk
    return "@" + u.username


@api_view(["GET"])
@permission_classes([AllowAny])
def board(request):
    """Leaderboard: everyone's points and active time. period = today | all."""
    from django.contrib.auth import get_user_model
    c = campaign()
    out = _status(c)
    if not live(c) and not _staff(request.user):
        return Response(dict(out, rows=[]))
    today = request.GET.get("period") == "today"
    ev = PointEvent.objects.filter(user__is_active=True, user__is_blocked=False)
    act = DailyActivity.objects.all()
    if today:
        d = timezone.localdate()
        ev, act = ev.filter(day=d), act.filter(day=d)
    elif c.starts_at:
        ev, act = ev.filter(day__gte=timezone.localtime(c.starts_at).date()), act.filter(day__gte=timezone.localtime(c.starts_at).date())
    top = list(ev.values("user_id").annotate(p=Sum("points")).order_by("-p", "user_id")[:100])
    ids = [r["user_id"] for r in top]
    users = {u.pk: u for u in get_user_model().objects.filter(pk__in=ids)}
    mins = dict(act.filter(user_id__in=ids).values_list("user_id").annotate(s=Sum("active_seconds")))
    sp = __import__("rewards.models", fromlist=["Spin"]).Spin.objects.filter(user_id__in=ids, test=False)
    if today:
        sp = sp.filter(day=d)
    elif c.starts_at:
        sp = sp.filter(day__gte=timezone.localtime(c.starts_at).date())
    spins = dict(sp.values_list("user_id").annotate(n=Count("id")))
    refs = __import__("rewards.views", fromlist=["qualified_counts"]).qualified_counts(c.starts_at)
    rows = []
    for i, r in enumerate(top, 1):
        u = users.get(r["user_id"])
        if u:
            rows.append({"rank": i, "name": _label(u), "points": r["p"], "minutes": (mins.get(u.pk) or 0) // 60,
                         "spins": spins.get(u.pk, 0), "referrals": refs.get(u.pk, 0), "me": request.user.is_authenticated and u.pk == request.user.pk})
    return Response(dict(out, period="today" if today else "all", rows=rows))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """My points today and in total, my active minutes and which sections I used today."""
    u, c, d = request.user, campaign(), timezone.localdate()
    mine = PointEvent.objects.filter(user=u)
    if c.starts_at:
        mine = mine.filter(day__gte=timezone.localtime(c.starts_at).date())
    t = mine.filter(day=d)
    by_kind = dict(t.values_list("kind").annotate(p=Sum("points")))
    act = DailyActivity.objects.filter(user=u, day=d).first()
    return Response(dict(_status(c), counting=counts_for(u, c), today=sum(by_kind.values()), total=mine.aggregate(p=Sum("points"))["p"] or 0,
                         by_kind=by_kind, sections=sorted({SECTION.get(k, k) for k in by_kind} - {"time"}),
                         minutes_today=(act.active_seconds if act else 0) // 60))


# ================= stage 2: lucky wheel, rewards balance, winners =================
from django.db import transaction                                        # noqa: E402
from django.db.models import Count, Q                                    # noqa: E402

from .models import PrizeSlot, RewardEntry, Spin                         # noqa: E402

WHEEL_PER_DAY = 100            # one Rs 100 wheel prize a day
WHEEL_BUDGET = 3000            # wheel share of the Rs 10,000 (referral draws 4,000; Rs 3,000 not yet assigned)
SPIN_POINTS = 30               # points needed today for the daily spin
EXPLORER_SECTIONS = 5          # sections used today for the bonus spin
NO_REPEAT_DAYS = 7             # a wheel winner cannot win the wheel again for 7 days
PRIZE_KINDS = ("win", "scratch", "draw")


def _no_prizes(u):
    """Staff and moderators run the campaign, so they can only make test spins."""
    return bool(u.is_staff or u.is_superuser or getattr(u, "is_moderator", False))


def given_total():
    return RewardEntry.objects.filter(kind__in=PRIZE_KINDS).aggregate(s=Sum("amount"))["s"] or 0


def _today_points(u, d):
    ev = PointEvent.objects.filter(user=u, day=d)
    pts = ev.aggregate(s=Sum("points"))["s"] or 0
    sections = sorted({SECTION.get(k, k) for k in ev.values_list("kind", flat=True)} - {"time"})
    return pts, sections


def _spin_state(u, d):
    pts, sections = _today_points(u, d)
    used = set(Spin.objects.filter(user=u, day=d).values_list("kind", flat=True))
    ok = {"daily": pts >= SPIN_POINTS, "explorer": len(sections) >= EXPLORER_SECTIONS}
    left = [k for k in ("daily", "explorer") if ok[k] and k not in used]
    return {"points_today": pts, "sections": sections, "need_points": SPIN_POINTS, "need_sections": EXPLORER_SECTIONS,
            "daily_ok": ok["daily"], "explorer_ok": ok["explorer"], "used": sorted(used), "left": len(left), "next": left[0] if left else ""}


def balance(u):
    return RewardEntry.objects.filter(user=u).aggregate(s=Sum("amount"))["s"] or 0


def _wheel_today():
    """Public: what happened to today's wheel prize (never shows a future release time)."""
    now, d = timezone.now(), timezone.localdate()
    won = list(PrizeSlot.objects.filter(kind="wheel", won_at__date=d).select_related("won_by").order_by("won_at"))
    waiting = PrizeSlot.objects.filter(kind="wheel", release_at__lte=now, won_by__isnull=True).count()
    later = PrizeSlot.objects.filter(kind="wheel", release_at__gt=now, release_at__date=d).count()
    return {"won_today": [{"name": _label(s.won_by), "amount": s.amount} for s in won if s.won_by],
            "waiting": waiting, "still_to_come_today": later}


def make_slots(c):
    """Called when the campaign is switched on: one Rs 100 wheel prize per day at a secret random
    time between 9 am and 11 pm (Pakistan time), within the wheel budget. Prizes not yet won are redrawn."""
    import secrets
    from datetime import datetime, time
    PrizeSlot.objects.filter(kind="wheel", won_by__isnull=True).delete()
    left = WHEEL_BUDGET - (PrizeSlot.objects.filter(kind="wheel").aggregate(s=Sum("amount"))["s"] or 0)
    d, last = timezone.localtime(c.starts_at).date(), timezone.localtime(c.ends_at - timedelta(seconds=1)).date()
    won_days = set(PrizeSlot.objects.filter(kind="wheel").values_list("won_at__date", flat=True))
    made = 0
    while d <= last and left >= WHEEL_PER_DAY:
        if d not in won_days:
            at = timezone.make_aware(datetime.combine(d, time(9, 0))) + timedelta(seconds=secrets.randbelow(14 * 3600))
            PrizeSlot.objects.create(kind="wheel", amount=WHEEL_PER_DAY, release_at=at)
            left -= WHEEL_PER_DAY
            made += 1
        d += timedelta(days=1)
    return made


@api_view(["GET"])
@permission_classes([AllowAny])
def state(request):
    """Everything the rewards page needs, in one call."""
    u, c = request.user, campaign()
    out = dict(_status(c), given=given_total(), wheel=_wheel_today(), wheel_prize=WHEEL_PER_DAY,
               rules={"spin_points": SPIN_POINTS, "explorer_sections": EXPLORER_SECTIONS, "no_repeat_days": NO_REPEAT_DAYS},
               draws=__import__("rewards.views", fromlist=["_draws_out"])._draws_out())
    if u.is_authenticated:
        d = timezone.localdate()
        out["me"] = dict(_spin_state(u, d), name=_label(u), counting=counts_for(u, c), balance=balance(u),
                         email_verified=bool(getattr(u, "is_email_verified", True)), can_win=not _no_prizes(u),
                         minutes_today=(DailyActivity.objects.filter(user=u, day=d).values_list("active_seconds", flat=True).first() or 0) // 60,
                         total=PointEvent.objects.filter(user=u, **({"day__gte": timezone.localtime(c.starts_at).date()} if c.starts_at else {})).aggregate(s=Sum("points"))["s"] or 0,
                         history=[{"amount": e.amount, "kind": e.kind, "note": e.note, "when": timezone.localtime(e.created_at).strftime("%d %b %Y %H:%M")}
                                  for e in RewardEntry.objects.filter(user=u).order_by("-id")[:20]])
    return Response(out)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def spin(request):
    u, c = request.user, campaign()
    if not counts_for(u, c):
        return Response({"detail": "The rewards campaign has not started yet."}, status=404)
    if not getattr(u, "is_email_verified", True):
        return Response({"detail": "Verify your email first, then come back to spin."}, status=400)
    now, d = timezone.now(), timezone.localdate()
    st = _spin_state(u, d)
    if not st["next"]:
        need = "Earn %d points today for your daily spin" % SPIN_POINTS if not st["daily_ok"] else "Use %d different sections today for a bonus spin" % EXPLORER_SECTIONS
        return Response({"detail": "No spin left today. " + need + "."}, status=400)
    test = (not live(c)) or _no_prizes(u)
    won = 0
    with transaction.atomic():
        try:
            s = Spin.objects.create(user=u, day=d, kind=st["next"], test=test)
        except IntegrityError:
            return Response({"detail": "That spin was already used."}, status=400)
        recent = RewardEntry.objects.filter(user=u, kind="win", created_at__gte=now - timedelta(days=NO_REPEAT_DAYS)).exists()
        if not test and not recent:
            slot = (PrizeSlot.objects.select_for_update(skip_locked=True)
                    .filter(kind="wheel", release_at__lte=now, won_by__isnull=True).order_by("release_at").first())
            if slot and given_total() + slot.amount <= c.budget:
                slot.won_by, slot.won_at = u, now
                slot.save(update_fields=["won_by", "won_at"])
                RewardEntry.objects.create(user=u, amount=slot.amount, kind="win", note="Lucky wheel")
                s.amount, s.slot = slot.amount, slot
                s.save(update_fields=["amount", "slot"])
                won = slot.amount
    msg = ("You won Rs %d! It is in your rewards balance." % won) if won else \
          ("Test spin: no money in test mode or for staff." if test else
           ("You already won in the last %d days, so this spin cannot win. Others get a turn." % NO_REPEAT_DAYS) if recent else
           "Not this time. Try again tomorrow.")
    return Response({"won": won, "test": test, "message": msg, "me": dict(_spin_state(u, d), balance=balance(u))})


@api_view(["GET"])
@permission_classes([AllowAny])
def winners(request):
    """Public list of every prize given, so anyone can check the campaign."""
    rows = RewardEntry.objects.filter(kind__in=PRIZE_KINDS).select_related("user").order_by("-id")[:200]
    from .models import Withdrawal as _W
    pays = _W.objects.filter(status="paid").select_related("user").order_by("-handled_at")[:200]
    return Response({"given": given_total(), "budget": campaign().budget,
                     "paid": sum(w.amount for w in pays),
                     "rows": [{"name": _label(e.user), "amount": e.amount, "how": e.note or e.kind,
                               "when": timezone.localtime(e.created_at).strftime("%d %b %Y %H:%M")} for e in rows],
                     "payouts": [{"name": _label(w.user), "amount": w.amount, "how": dict(_W.METHODS).get(w.method, w.method),
                                  "when": timezone.localtime(w.handled_at).strftime("%d %b %Y %H:%M") if w.handled_at else ""} for w in pays]})


# ================= stage 3a: claim steps, withdrawals, admin payouts =================
import os                                                                 # noqa: E402
import re                                                                 # noqa: E402
import secrets as _secrets                                                # noqa: E402

from django.contrib.auth import get_user_model                           # noqa: E402
from django.http import FileResponse, Http404                            # noqa: E402
from rest_framework.decorators import parser_classes                     # noqa: E402
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser  # noqa: E402

from .models import RewardSteps, Withdrawal                              # noqa: E402

MIN_WITHDRAW = 100             # rupees
KYC_ABOVE = 1000               # paid out in total above this needs the ID check (blue-tick KYC)
IRC_CHECK = True               # XpertBot confirms "!claim <code>" typed in #xpertcreation (stage 3b)
MAX_PROOF = 8 * 1024 * 1024
SCRATCH_NETWORKS = ("jazz", "zong", "telenor", "ufone")
SCRATCH_AMOUNTS = (100, 300, 500, 1000)
POST_TEXT = "I am earning rewards on XpertCreation: use the site, earn points and spin the lucky wheel. Free for everyone: https://xpertcreation.com/rewards"
METHOD_NAMES = dict(Withdrawal.METHODS)


def _staff_only(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def _steps(u):
    s = RewardSteps.objects.filter(user=u).first()
    if not s:
        for _ in range(5):
            code = "XC-" + "".join(_secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5))
            try:
                s = RewardSteps.objects.create(user=u, code=code)
                break
            except IntegrityError:
                continue
    return s


def _steps_out(s, c):
    need = {"post": True, "irc": IRC_CHECK, "youtube": bool(c.youtube_url), "facebook": bool(c.facebook_url)}
    done = {"post": bool(s.post_at), "irc": bool(s.irc_at), "youtube": bool(s.youtube_at), "facebook": bool(s.facebook_at)}
    return {"code": s.code, "need": need, "done": done, "all_done": all(done[k] for k in need if need[k]),
            "youtube_url": c.youtube_url, "facebook_url": c.facebook_url, "post_text": POST_TEXT, "irc_ready": IRC_CHECK}


def _kyc_ok(u):
    k = getattr(u, "person_kyc", None)
    try:
        return bool(k and k.status == "approved")
    except Exception:
        return False


def _w_out(w, admin=False):
    d = {"id": w.id, "amount": w.amount, "method": w.method, "method_label": METHOD_NAMES.get(w.method, w.method),
         "country": w.country, "status": w.status, "note": w.admin_note, "details": w.details,
         "when": timezone.localtime(w.created_at).strftime("%d %b %Y %H:%M"),
         "handled": timezone.localtime(w.handled_at).strftime("%d %b %Y %H:%M") if w.handled_at else "",
         "proof": bool(w.proof_path), "account_name": w.account_name, "account_no": w.account_no,
         "bank_name": w.bank_name, "network": w.network,
         "card": bool(w.card_pin) and w.status == "paid", "revealed": bool(w.revealed_at), "loaded": bool(w.loaded_at)}
    if admin:
        u = w.user
        d.update({"member": _label(u), "user_id": u.pk, "email": u.email, "balance": balance(u), "kyc": _kyc_ok(u),
                  "paid_before": Withdrawal.objects.filter(user=u, status="paid").aggregate(s=Sum("amount"))["s"] or 0,
                  "pin_saved": bool(w.card_pin)})
    return d


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet(request):
    u, c = request.user, campaign()
    paid = Withdrawal.objects.filter(user=u, status__in=["requested", "paid"]).aggregate(s=Sum("amount"))["s"] or 0
    return Response({"balance": balance(u), "steps": _steps_out(_steps(u), c), "kyc": _kyc_ok(u), "paid_total": paid,
                     "rules": {"min": MIN_WITHDRAW, "kyc_above": KYC_ABOVE}, "methods": Withdrawal.METHODS,
                     "withdrawals": [_w_out(w) for w in Withdrawal.objects.filter(user=u).order_by("-id")[:20]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def step(request):
    """which = post (checks for your XpertConnect post with the rewards link), youtube or facebook (you confirm)."""
    u, c = request.user, campaign()
    s, which, now = _steps(u), str(request.data.get("which") or ""), timezone.now()
    if which == "post":
        if not s.post_at:
            from django.apps import apps
            P = apps.get_model("feed", "Post")
            p = (P.objects.filter(author=u, hidden=False, visibility__in=["public", "members"], created_at__gte=s.created_at)
                 .filter(body__icontains="xpertcreation.com/rewards").order_by("-id").first())
            if not p:
                return Response({"detail": "We could not find your post yet. Post it on XpertConnect (Everyone or Members) with the link xpertcreation.com/rewards, then tap Check again."}, status=400)
            s.post_id, s.post_at = p.pk, now
            s.save(update_fields=["post_id", "post_at"])
    elif which in ("youtube", "facebook"):
        if not getattr(c, which + "_url"):
            return Response({"detail": "This step is not needed."}, status=400)
        if not getattr(s, which + "_at"):
            setattr(s, which + "_at", now)
            s.save(update_fields=[which + "_at"])
    else:
        return Response({"detail": "Unknown step."}, status=400)
    return Response({"steps": _steps_out(s, c)})


def _digits(x):
    return re.sub(r"\D", "", str(x or ""))[:40]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request):
    u, c, d = request.user, campaign(), request.data
    if getattr(u, "is_blocked", False):
        return Response({"detail": "Your account cannot withdraw."}, status=403)
    s = _steps_out(_steps(u), c)
    if not s["all_done"]:
        return Response({"detail": "Finish the steps above first."}, status=400)
    method = str(d.get("method") or "")
    if method not in METHOD_NAMES:
        return Response({"detail": "Choose how you want to be paid."}, status=400)
    try:
        amount = int(d.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount < MIN_WITHDRAW:
        return Response({"detail": "The smallest withdrawal is Rs %d." % MIN_WITHDRAW}, status=400)
    country = re.sub(r"[^A-Z]", "", str(d.get("country") or "PK").upper())[:2] or "PK"
    name, acc = str(d.get("account_name") or "").strip()[:80], str(d.get("account_no") or "").strip()[:40]
    bank, network, details = str(d.get("bank_name") or "").strip()[:80], str(d.get("network") or "").strip()[:20], str(d.get("details") or "").strip()[:500]
    if method in ("easypaisa", "jazzcash", "load") and len(_digits(acc)) < 10:
        return Response({"detail": "Enter the mobile number to pay."}, status=400)
    if method in ("easypaisa", "jazzcash", "bank") and not name:
        return Response({"detail": "Enter the account holder's name."}, status=400)
    if method == "bank" and (not bank or len(acc) < 6):
        return Response({"detail": "Enter the bank name and the account number or IBAN."}, status=400)
    if method in ("easypaisa", "jazzcash", "bank") and country != "PK":
        return Response({"detail": "EasyPaisa, JazzCash and Pakistani bank transfers are for Pakistan. Choose Other and tell us how to pay you."}, status=400)
    if method == "scratch":
        if network.lower() not in SCRATCH_NETWORKS:
            return Response({"detail": "Choose the network for your scratch card: Jazz, Zong, Telenor or Ufone."}, status=400)
        if amount not in SCRATCH_AMOUNTS:
            return Response({"detail": "Scratch cards come in Rs 100, 300, 500 or 1,000."}, status=400)
        if country != "PK":
            return Response({"detail": "Scratch cards are Pakistani mobile cards. Choose Other and tell us how to pay you."}, status=400)
        network = network.capitalize()
    if method == "other" and len(details) < 10:
        return Response({"detail": "Tell us how you would like to be paid in your country."}, status=400)
    key = _digits(acc) if method not in ("other", "scratch") else ""
    if key and Withdrawal.objects.filter(account_key=key).exclude(user=u).exclude(status__in=["rejected", "cancelled"]).exists():
        return Response({"detail": "This account number is already used by another member. Each member must use their own account."}, status=400)
    with transaction.atomic():
        get_user_model().objects.select_for_update().filter(pk=u.pk).first()      # one request at a time per member
        if Withdrawal.objects.filter(user=u, status="requested").exists():
            return Response({"detail": "You already have a request waiting. Wait until it is paid."}, status=400)
        if amount > balance(u):
            return Response({"detail": "Your balance is Rs %d." % balance(u)}, status=400)
        before = Withdrawal.objects.filter(user=u, status="paid").aggregate(s=Sum("amount"))["s"] or 0
        if before + amount > KYC_ABOVE and not _kyc_ok(u):
            return Response({"detail": "Withdrawals above Rs %d in total need the identity check first (the same as the blue tick). Open xpertcreation.com/get-verified." % KYC_ABOVE, "kyc": True}, status=400)
        w = Withdrawal.objects.create(user=u, amount=amount, method=method, country=country, account_name=name, account_no=acc,
                                      account_key=key, bank_name=bank, network=network, details=details)
        RewardEntry.objects.create(user=u, amount=-amount, kind="withdraw", note="Withdrawal #%d (%s)" % (w.id, METHOD_NAMES[method]))
    try:
        from notifications.views import notify_admins
        notify_admins("reward", "Rewards withdrawal #%d: Rs %d by %s (%s)" % (w.id, amount, _label(u), METHOD_NAMES[method]), "/rewards-admin")
    except Exception:
        pass
    return Response({"withdrawal": _w_out(w), "balance": balance(u)}, status=201)


def _close(w, status, by, note):
    """Reject or cancel: put the money back in the balance."""
    w.status, w.handled_by, w.handled_at = status, by, timezone.now()
    if note:
        w.admin_note = note[:300]
    w.save()
    RewardEntry.objects.create(user=w.user, amount=w.amount, kind="adjust",
                               note="Withdrawal #%d %s - money back in your balance" % (w.id, "cancelled" if status == "cancelled" else "not paid"))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw_cancel(request, pk):
    with transaction.atomic():
        w = Withdrawal.objects.select_for_update().filter(pk=pk, user=request.user, status="requested").first()
        if not w:
            return Response({"detail": "Request not found."}, status=404)
        _close(w, "cancelled", request.user, "")
    return Response({"withdrawal": _w_out(w), "balance": balance(request.user)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_list(request):
    if not _staff_only(request.user):
        return Response({"detail": "Staff only."}, status=403)
    st = request.GET.get("status") or "requested"
    qs = Withdrawal.objects.select_related("user").order_by("id" if st == "requested" else "-id")
    if st != "all":
        qs = qs.filter(status=st)
    given, paid = given_total(), Withdrawal.objects.filter(status="paid").aggregate(s=Sum("amount"))["s"] or 0
    waiting = Withdrawal.objects.filter(status="requested").aggregate(s=Sum("amount"), n=Count("id"))
    return Response({"rows": [_w_out(w, True) for w in qs[:200]], "given": given, "paid": paid,
                     "waiting": waiting["s"] or 0, "waiting_n": waiting["n"] or 0, "budget": campaign().budget})


def _save_proof(f, wid):
    from companies.views import DOCS
    from PIL import Image, ImageOps
    if f.size > MAX_PROOF:
        raise ValueError("The screenshot is over 8 MB.")
    try:
        im = Image.open(f); im.load()
    except Exception:
        raise ValueError("That file is not a picture we can read.")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((2000, 2000))
    rel = os.path.join("reward_proofs", timezone.localdate().strftime("%Y%m"), "%d_%s.webp" % (wid, _secrets.token_hex(8)))
    full = os.path.join(DOCS, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    im.save(full, "WEBP", quality=82)
    return rel


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def admin_act(request, pk):
    """action = paid (with the payment screenshot) or reject (money goes back to the member's balance)."""
    u = request.user
    if not _staff_only(u):
        return Response({"detail": "Staff only."}, status=403)
    action, note = str(request.data.get("action") or ""), str(request.data.get("note") or "").strip()[:300]
    with transaction.atomic():
        w = Withdrawal.objects.select_for_update().select_related("user").filter(pk=pk, status="requested").first()
        if not w:
            return Response({"detail": "Request not found or already handled."}, status=404)
        if action == "paid":
            f = request.FILES.get("proof")
            pin = str(request.data.get("pin") or "").strip()[:300]
            if w.method == "scratch":
                if len(_digits(pin)) < 8:
                    return Response({"detail": "Type the scratch card PIN (the numbers under the silver strip)."}, status=400)
                w.card_pin = pin
            elif not f:
                return Response({"detail": "Upload the payment screenshot."}, status=400)
            if f:
                try:
                    w.proof_path = _save_proof(f, w.id)
                except ValueError as e:
                    return Response({"detail": str(e)}, status=400)
            w.status, w.handled_by, w.handled_at, w.admin_note = "paid", u, timezone.now(), note
            w.save()
            text = ("Your Rs %d %s scratch card is ready. Open Rewards and scratch it to see the PIN." % (w.amount, w.network)) if w.method == "scratch" \
                else "Your rewards withdrawal of Rs %d is paid (%s)." % (w.amount, METHOD_NAMES.get(w.method, w.method))
        elif action == "reject":
            if not note:
                return Response({"detail": "Write the reason, so the member knows."}, status=400)
            _close(w, "rejected", u, note)
            text = "Your rewards withdrawal of Rs %d was not paid: %s. The money is back in your balance." % (w.amount, note)
        elif action == "note":
            if not note:
                return Response({"detail": "Write a message."}, status=400)
            w.admin_note = note
            w.save(update_fields=["admin_note"])
            text = "Message about your withdrawal #%d: %s" % (w.id, note)
        else:
            return Response({"detail": "Unknown action."}, status=400)
    try:
        from notifications.views import notify
        notify(w.user, "reward", text[:200], "/rewards")
    except Exception:
        pass
    return Response({"withdrawal": _w_out(w, True)})


def proof(request, pk):
    """The payment screenshot: only the member it belongs to and staff; staff openings are logged."""
    u = request.user
    w = Withdrawal.objects.filter(pk=pk).first()
    if not u.is_authenticated or not w or not w.proof_path or not (w.user_id == u.pk or _staff_only(u)):
        raise Http404
    from companies.views import DOCS
    full = os.path.join(DOCS, w.proof_path)
    if not os.path.exists(full):
        raise Http404
    if w.user_id != u.pk:
        try:
            from auditlog.models import AuditEvent
            AuditEvent.objects.create(user=u, action="reward_proof_view", target="withdrawal %d" % w.id)
        except Exception:
            pass
    r = FileResponse(open(full, "rb"), as_attachment=False, filename="payment-%d.webp" % w.id)
    r["X-Content-Type-Options"] = "nosniff"
    r["Cache-Control"] = "private, no-store"
    return r


# ================= stage 3b: IRC !claim check and scratch card payouts =================
from django.views.decorators.csrf import csrf_exempt                     # noqa: E402




@csrf_exempt
def irc_claim(request):
    """Called only by XpertBot (header X-IRC-Bot-Secret, same check as !post). The bot sends the IRC account
    the member is signed in as and the code from their rewards page."""
    import json as _json
    from django.http import JsonResponse
    from ircbot.views import _ok
    if request.method != "POST" or not _ok(request):
        return JsonResponse({"detail": "Not allowed."}, status=403)
    try:
        d = _json.loads(request.body.decode() or "{}")
    except Exception:
        d = {}
    acct, code = str(d.get("account") or "").strip(), str(d.get("code") or "").strip().upper()
    u = get_user_model().objects.filter(username__iexact=acct, is_active=True).first() if acct else None
    if not u:
        return JsonResponse({"detail": "No XpertCreation member with that name."}, status=404)
    s = RewardSteps.objects.filter(user=u).first()
    if not s or s.code != code:
        return JsonResponse({"detail": "That is not your code. Copy it from xpertcreation.com/rewards (signed in as %s)." % u.username}, status=400)
    if not s.irc_at:
        s.irc_at = timezone.now()
        s.save(update_fields=["irc_at"])
    return JsonResponse({"ok": True, "detail": "Done! The IRC step is complete for %s. Go back to xpertcreation.com/rewards." % u.username})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def card(request, pk):
    """The member's own scratch card: action reveal (gives the PIN while they scratch) or loaded (they used it)."""
    w = Withdrawal.objects.filter(pk=pk, user=request.user, method="scratch", status="paid").first()
    if not w or not w.card_pin:
        return Response({"detail": "Card not found."}, status=404)
    action, now = str(request.data.get("action") or "reveal"), timezone.now()
    if action == "reveal":
        if not w.revealed_at:
            w.revealed_at = now
            w.save(update_fields=["revealed_at"])
        return Response({"pin": w.card_pin, "network": w.network, "amount": w.amount})
    if action == "loaded":
        if not w.loaded_at:
            w.loaded_at = now
            w.save(update_fields=["loaded_at"])
        return Response({"ok": True})
    return Response({"detail": "Unknown action."}, status=400)


# ================= stage 4: referrals, commissions, referral draws =================
from .models import Commission, Referral, ReferralDraw                   # noqa: E402

REF_COOKIE = "xc_ref"
REF_MAX_AGE_DAYS = 14          # only accounts this new can be linked to a referrer
COMMISSION = {1: 10, 2: 5}     # percent of every real payment: inviter, inviter's inviter
COMMISSION_HOLD_DAYS = 7
QUALIFY_POINTS, QUALIFY_DAYS = 30, 3
SAME_IP_LIMIT = 3              # more referrals than this from one sign-up IP do not qualify
REAL_PROVIDER = "safepay-production"    # test-mode and sandbox payments never pay a commission
# Referral prizes, Rs 7,000 of the Rs 10,000 (the wheel has the other Rs 3,000):
#   10+ qualified referrals: Rs 500 draw on days 7, 14, 21, 28
#   50+ qualified referrals: Rs 1,000 draw on days 15 and 30, and Rs 3,000 shared equally on the last day
DRAW_PLAN = [(10, "draw", 500, 7), (10, "draw", 500, 14), (10, "draw", 500, 21), (10, "draw", 500, 28),
             (50, "draw", 1000, 15), (50, "draw", 1000, 30), (50, "share", 3000, 30)]


def attach_referral(user, username):
    """Link a new member to the member whose /r/ link they came from. Returns True when linked."""
    if not user or not user.is_authenticated or not username:
        return False
    if Referral.objects.filter(user=user).exists():
        return False
    joined = getattr(user, "date_joined", None)
    if joined and joined < timezone.now() - timedelta(days=REF_MAX_AGE_DAYS):
        return False
    ref = get_user_model().objects.filter(username__iexact=str(username)[:20], is_active=True).first()
    if not ref or ref.pk == user.pk or getattr(ref, "is_blocked", False):
        return False
    up = Referral.objects.filter(user=ref).first()
    if up and up.referrer_id == user.pk:                 # no two-way loops
        return False
    try:
        Referral.objects.create(user=user, referrer=ref)
        return True
    except IntegrityError:
        return False


def qualify_referrals():
    """A referral counts once the new member verified their email and earned 30+ points on 3+ different days.
    Referrals from a sign-up IP that already has 3 counted referrals do not count."""
    n = 0
    for r in Referral.objects.filter(qualified_at__isnull=True).select_related("user")[:2000]:
        u = r.user
        if not getattr(u, "is_email_verified", True) or getattr(u, "is_blocked", False):
            continue
        days = (PointEvent.objects.filter(user=u).values("day").annotate(p=Sum("points")).filter(p__gt=0))
        if len(days) < QUALIFY_DAYS or sum(d["p"] for d in days) < QUALIFY_POINTS:
            continue
        ip = getattr(u, "signup_ip", None)
        if ip and Referral.objects.filter(referrer_id=r.referrer_id, qualified_at__isnull=False, user__signup_ip=ip).count() >= SAME_IP_LIMIT:
            continue
        r.qualified_at = timezone.now()
        r.save(update_fields=["qualified_at"])
        n += 1
    return n


def run_commissions():
    """Every real paid order of a referred member gives commissions; refunds take them back."""
    from shop.models import Order
    now, made, released, reversed_ = timezone.now(), 0, 0, 0
    refs = dict(Referral.objects.values_list("user_id", "referrer_id"))
    if refs:
        for o in Order.objects.filter(status="paid", provider=REAL_PROVIDER, user_id__in=list(refs)).only("id", "user_id", "amount", "paid_at"):
            r1 = Referral.objects.filter(user_id=o.user_id).first()
            if not r1 or not o.paid_at or o.paid_at < r1.created_at:
                continue                                     # only payments made after the referral link
            chain = [(1, r1.referrer_id)]
            r2 = Referral.objects.filter(user_id=r1.referrer_id).first()
            if r2 and r2.referrer_id != o.user_id:
                chain.append((2, r2.referrer_id))
            for level, ref_id in chain:
                amt = int(o.amount) * COMMISSION[level] // 100
                if amt <= 0:
                    continue
                _, c = Commission.objects.get_or_create(order_id=o.id, level=level, defaults={
                    "referrer_id": ref_id, "buyer_id": o.user_id, "order_amount": o.amount, "amount": amt,
                    "release_at": o.paid_at + timedelta(days=COMMISSION_HOLD_DAYS)})
                made += c
    paid = set(Order.objects.filter(status="paid", id__in=list(Commission.objects.exclude(status="reversed").values_list("order_id", flat=True))).values_list("id", flat=True))
    for c in Commission.objects.exclude(status="reversed").select_related("buyer"):
        who = _label(c.buyer)
        if c.order_id not in paid:                          # refunded or cancelled
            with transaction.atomic():
                if c.status == "released":
                    RewardEntry.objects.create(user_id=c.referrer_id, amount=-c.amount, kind="commission",
                                               note="Referral share taken back: %s's order was refunded" % who)
                c.status = "reversed"
                c.save(update_fields=["status"])
            reversed_ += 1
        elif c.status == "held" and c.release_at <= now:
            with transaction.atomic():
                RewardEntry.objects.create(user_id=c.referrer_id, amount=c.amount, kind="commission",
                                           note="Referral share (level %d): %s paid Rs %d" % (c.level, who, c.order_amount))
                c.status = "released"
                c.save(update_fields=["status"])
            released += 1
    return made, released, reversed_


def make_draws(c):
    """Called when the campaign is switched on: schedule the referral prizes on their days (9 pm Pakistan time).
    Draws already done are kept."""
    from datetime import datetime, time
    ReferralDraw.objects.filter(done_at__isnull=True).delete()
    start = timezone.localtime(c.starts_at).date()
    days = max(1, (c.ends_at - c.starts_at).days)
    done = set(ReferralDraw.objects.values_list("tier", "kind", "amount", "note"))
    n = 0
    for tier, kind, amount, day in DRAW_PLAN:
        d = min(day, days)
        note = "day %d" % day
        if (tier, kind, amount, note) in done:
            continue
        at = timezone.make_aware(datetime.combine(start + timedelta(days=d - 1), time(21, 0)))
        ReferralDraw.objects.create(tier=tier, kind=kind, amount=amount, draw_at=at, note=note)
        n += 1
    return n


def qualified_counts(since=None):
    qs = Referral.objects.filter(qualified_at__isnull=False)
    if since:
        qs = qs.filter(created_at__gte=since)
    return dict(qs.values_list("referrer_id").annotate(n=Count("id")))


def run_draws(c=None):
    """Run every draw whose time has come. A tier with nobody in it keeps its prize for its next draw;
    on the last day anything still unclaimed goes to a draw among everyone with at least 1 qualified referral."""
    import secrets
    c = c or campaign()
    now, out = timezone.now(), []
    if not c.starts_at:
        return out
    counts = qualified_counts(c.starts_at)
    U = get_user_model()
    ok_ids = set(U.objects.filter(pk__in=list(counts), is_active=True, is_blocked=False, is_staff=False, is_superuser=False)
                 .exclude(**({"is_moderator": True} if hasattr(U, "is_moderator") else {})).values_list("pk", flat=True))
    for dr in ReferralDraw.objects.filter(done_at__isnull=True, draw_at__lte=now).order_by("draw_at", "id"):
        pool = sorted(uid for uid in ok_ids if counts.get(uid, 0) >= dr.tier)
        last = dr.draw_at >= c.ends_at - timedelta(days=1)
        if not pool:
            nxt = ReferralDraw.objects.filter(done_at__isnull=True, tier=dr.tier, kind="draw", draw_at__gt=dr.draw_at).order_by("draw_at").first()
            if nxt and not last:
                nxt.amount += dr.amount
                nxt.save(update_fields=["amount"])
                dr.done_at, dr.note = now, (dr.note + ": nobody had %d+ yet, prize moved to the next draw" % dr.tier)[:200]
                dr.save(update_fields=["done_at", "note"])
                continue
            pool = sorted(uid for uid in ok_ids if counts.get(uid, 0) >= 1)
            if not pool:
                if now > c.ends_at + timedelta(days=1):
                    dr.done_at, dr.note = now, (dr.note + ": nobody qualified, not given")[:200]
                    dr.save(update_fields=["done_at", "note"])
                continue
            dr.note = (dr.note + ": nobody had %d+, open to everyone with 1+" % dr.tier)[:200]
        if given_total() + dr.amount > c.budget:
            dr.done_at, dr.note = now, (dr.note + ": budget used up")[:200]
            dr.save(update_fields=["done_at", "note"])
            continue
        if dr.kind == "share":
            each = dr.amount // len(pool)
            wins = [{"user": uid, "amount": each} for uid in pool] if each > 0 else []
        else:
            wins = [{"user": secrets.choice(pool), "amount": dr.amount}]
        with transaction.atomic():
            for w in wins:
                RewardEntry.objects.create(user_id=w["user"], amount=w["amount"], kind="draw",
                                           note="Referral %s (%d+ referrals)" % ("share" if dr.kind == "share" else "draw", dr.tier))
                try:
                    from notifications.views import notify
                    notify(U.objects.get(pk=w["user"]), "reward", "You won Rs %d in the referral %s! It is in your rewards balance." % (w["amount"], "share" if dr.kind == "share" else "draw"), "/rewards")
                except Exception:
                    pass
            dr.winners, dr.done_at = wins, now
            dr.save(update_fields=["winners", "done_at", "note"])
        out.append(dr.id)
    return out


def _draws_out():
    U = get_user_model()
    rows = []
    for d in ReferralDraw.objects.order_by("draw_at", "id"):
        names = {u.pk: _label(u) for u in U.objects.filter(pk__in=[w["user"] for w in (d.winners or [])])}
        rows.append({"tier": d.tier, "kind": d.kind, "amount": d.amount, "when": timezone.localtime(d.draw_at).strftime("%d %b %Y, %I %p"),
                     "done": bool(d.done_at), "note": d.note.split(": ", 1)[1] if ": " in d.note else "",
                     "winners": [{"name": names.get(w["user"], "Member"), "amount": w["amount"]} for w in (d.winners or [])]})
    return rows


@api_view(["GET"])
@permission_classes([AllowAny])
def ref_card(request, username):
    """Public: who is inviting you (for the /r/<username> page). Name only, nothing private."""
    u = get_user_model().objects.filter(username__iexact=str(username)[:20], is_active=True).first()
    if not u or getattr(u, "is_blocked", False):
        return Response({"detail": "No member with that name."}, status=404)
    return Response({"username": u.username, "name": (getattr(u, "full_name", "") or u.username)[:60]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invite(request):
    u, c = request.user, campaign()
    mine = Referral.objects.filter(referrer=u)
    since = c.starts_at
    q = mine.filter(qualified_at__isnull=False)
    qn = q.filter(created_at__gte=since).count() if since else q.count()
    lvl2 = Referral.objects.filter(referrer_id__in=list(mine.values_list("user_id", flat=True))).count()
    com = Commission.objects.filter(referrer=u)
    return Response({"username": u.username or "", "link": ("https://xpertcreation.com/r/" + u.username) if u.username else "",
                     "joined": mine.count(), "qualified": qn, "level2": lvl2,
                     "held": com.filter(status="held").aggregate(s=Sum("amount"))["s"] or 0,
                     "released": com.filter(status="released").aggregate(s=Sum("amount"))["s"] or 0,
                     "rates": COMMISSION, "hold_days": COMMISSION_HOLD_DAYS,
                     "qualify": {"points": QUALIFY_POINTS, "days": QUALIFY_DAYS}, "tiers": [10, 50],
                     "draws": _draws_out()})


@api_view(["GET"])
@permission_classes([AllowAny])
def draws(request):
    return Response({"draws": _draws_out()})
