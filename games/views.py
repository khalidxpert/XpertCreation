import random
import secrets

from django.db.models import Max
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import Score, Session, Stats

# Memory: pairs per level, and the emoji they are drawn from.
PAIRS = {"easy": 6, "medium": 8, "hard": 12}
FACES = ["🍎","🍌","🍇","🍓","🍊","🍉","🥝","🍑","🥑","🍒","🥕","🌽",
         "🐶","🐱","🦊","🐼","🦁","🐸","🐵","🦉","🐢","🦋","🐬","🦄"]

WIN_LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


class PlayThrottle(SimpleRateThrottle):
    scope = "games"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


# ------------------------------------------------------------------ memory

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PlayThrottle])
def memory_start(request):
    level = request.data.get("level")
    if level not in PAIRS:
        level = "easy"

    n = PAIRS[level]
    deck = random.sample(FACES, n) * 2
    random.shuffle(deck)

    Session.objects.filter(user=request.user, game=Score.MEMORY,
                           finished_at__isnull=True).delete()
    s = Session.objects.create(
        user=request.user, game=Score.MEMORY, level=level,
        token=secrets.token_urlsafe(18)[:32],
        state={"deck": deck, "found": [], "moves": 0})

    # The deck itself is not sent. The client asks what is under a card when it
    # turns one over, which is the only way a memory game can be honest.
    return Response({"token": s.token, "level": level,
                     "cards": len(deck), "pairs": n})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def memory_flip(request):
    """body: { token, a, b }  - the two positions turned over."""
    s = Session.objects.filter(token=request.data.get("token") or "",
                               user=request.user, game=Score.MEMORY,
                               finished_at__isnull=True).first()
    if not s:
        return _err("No game in progress.", status.HTTP_404_NOT_FOUND)
    if s.elapsed > Session.MAX_SECONDS:
        s.finished_at = timezone.now()
        s.save(update_fields=["finished_at"])
        return _err("That game timed out.", status.HTTP_410_GONE)

    deck = s.state["deck"]
    found = s.state["found"]
    try:
        a, b = int(request.data["a"]), int(request.data["b"])
    except (KeyError, TypeError, ValueError):
        return _err("Pick two cards.")
    if a == b or not (0 <= a < len(deck)) or not (0 <= b < len(deck)):
        return _err("Pick two different cards.")
    if a in found or b in found:
        return _err("That pair is already matched.")

    s.state["moves"] += 1
    match = deck[a] == deck[b]
    if match:
        found.extend([a, b])
        s.state["found"] = found

    done = len(found) == len(deck)
    s.save(update_fields=["state"])

    out = {"a": deck[a], "b": deck[b], "match": match,
           "moves": s.state["moves"], "done": done}

    if done:
        secs = int(s.elapsed)
        s.finished_at = timezone.now()
        s.save(update_fields=["finished_at"])

        # Fewer moves and less time score higher. The floor of 10 stops a very
        # slow win from coming out negative.
        pairs = len(deck) // 2
        perfect = pairs                      # the fewest possible moves
        points = max(10, int(1000 * perfect / max(perfect, s.state["moves"])
                             - secs * 2) * (pairs // 6 or 1))

        score = Score.objects.create(user=request.user, game=Score.MEMORY,
                                     level=s.level, points=points, seconds=secs,
                                     moves=s.state["moves"], won=True)
        st, _ = Stats.objects.get_or_create(user=request.user)
        st.record(score)
        best = Score.objects.filter(user=request.user, game=Score.MEMORY,
                                    level=s.level).aggregate(m=Max("points"))["m"] or 0
        # A bare number means nothing. Show what earned it.
        out.update({
            "points": points, "seconds": secs,
            "personal_best": best, "is_best": points >= best,
            "breakdown": [
                {"label": "Pairs found", "value": str(pairs)},
                {"label": "Moves taken", "value": "%d (best possible %d)"
                                                  % (s.state["moves"], perfect)},
                {"label": "Time", "value": "%dm %02ds" % (secs // 60, secs % 60)
                                           if secs >= 60 else "%d seconds" % secs},
            ],
        })

    return Response(out)


# ------------------------------------------------------------------ tic-tac-toe

def winner(board):
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def winning_line(board):
    """Which three squares won it, so the page can draw a line through them."""
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return [a, b, c]
    return None


def best_move(board, me, you, level):
    """
    Easy plays at random. Medium wins or blocks when it can. Hard plays
    minimax, which cannot be beaten - only drawn.
    """
    free = [i for i, v in enumerate(board) if not v]
    if not free:
        return None

    if level == "easy":
        return random.choice(free)

    for mark in (me, you):                 # win first, then block
        for i in free:
            test = list(board)
            test[i] = mark
            if winner(test) == mark:
                return i

    if level == "medium":
        for i in (4, 0, 2, 6, 8):
            if i in free:
                return i
        return random.choice(free)

    def minimax(b, turn):
        w = winner(b)
        if w == me:
            return 1, None
        if w == you:
            return -1, None
        spots = [i for i, v in enumerate(b) if not v]
        if not spots:
            return 0, None

        scores = []
        for i in spots:
            nb = list(b)
            nb[i] = turn
            sc, _ = minimax(nb, you if turn == me else me)
            scores.append((sc, i))
        return (max(scores) if turn == me else min(scores))

    return minimax(list(board), me)[1]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PlayThrottle])
def tictac_start(request):
    level = request.data.get("level")
    if level not in ("easy", "medium", "hard"):
        level = "medium"

    Session.objects.filter(user=request.user, game=Score.TICTAC,
                           finished_at__isnull=True).delete()
    s = Session.objects.create(
        user=request.user, game=Score.TICTAC, level=level,
        token=secrets.token_urlsafe(18)[:32],
        state={"board": [""] * 9, "you": "X", "bot": "O"})

    return Response({"token": s.token, "level": level,
                     "board": s.state["board"], "you": "X"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tictac_move(request):
    """body: { token, cell }"""
    s = Session.objects.filter(token=request.data.get("token") or "",
                               user=request.user, game=Score.TICTAC,
                               finished_at__isnull=True).first()
    if not s:
        return _err("No game in progress.", status.HTTP_404_NOT_FOUND)

    board = s.state["board"]
    you, bot = s.state["you"], s.state["bot"]

    try:
        cell = int(request.data["cell"])
    except (KeyError, TypeError, ValueError):
        return _err("Pick a square.")
    # The board lives on the server, so a client cannot play twice in a row or
    # drop a mark on an occupied square.
    if not (0 <= cell < 9) or board[cell]:
        return _err("That square is taken.")

    board[cell] = you
    result, bot_cell = None, None

    if winner(board) == you:
        result = "win"
    elif all(board):
        result = "draw"
    else:
        bot_cell = best_move(board, bot, you, s.level)
        if bot_cell is not None:
            board[bot_cell] = bot
        if winner(board) == bot:
            result = "lose"
        elif all(board):
            result = "draw"

    s.state["board"] = board
    s.save(update_fields=["state"])

    out = {"board": board, "bot_cell": bot_cell, "result": result,
           "win_line": winning_line(board)}

    if result:
        secs = int(s.elapsed)
        s.finished_at = timezone.now()
        s.save(update_fields=["finished_at"])

        base = {"win": 100, "draw": 40, "lose": 10}[result]
        mult = {"easy": 1, "medium": 2, "hard": 4}[s.level]
        points = base * mult

        score = Score.objects.create(user=request.user, game=Score.TICTAC,
                                     level=s.level, points=points, seconds=secs,
                                     moves=sum(1 for x in board if x),
                                     won=(result == "win"))
        st, _ = Stats.objects.get_or_create(user=request.user)
        st.record(score)
        out.update({
            "points": points, "streak": st.current_streak,
            "won_total": st.won, "played_total": st.played,
            "breakdown": [
                {"label": "Result", "value": {"win": "Won", "draw": "Drawn",
                                              "lose": "Lost"}[result]},
                {"label": "Difficulty", "value": s.level.capitalize()
                                                 + " (x%d)" % mult},
                {"label": "Day streak", "value": str(st.current_streak)},
            ],
        })

    return Response(out)


# ------------------------------------------------------------------ shared

@api_view(["GET"])
@permission_classes([AllowAny])
def leaderboard(request):
    game = request.GET.get("game", Score.MEMORY)
    level = request.GET.get("level", "easy")

    qs = Score.objects.filter(game=game, level=level)
    rows = (qs.values("user_id", "user__full_name", "user__email",
                      "user__hide_from_leaderboard")
              .annotate(best=Max("points")).order_by("-best")[:25])

    out, me = [], None
    for i, r in enumerate(rows, 1):
        name = ("Private player" if r["user__hide_from_leaderboard"]
                else ((r["user__full_name"] or "").strip() or r["user__email"].split("@")[0]))
        item = {"rank": i, "name": name, "points": r["best"]}
        out.append(item)
        if request.user.is_authenticated and r["user_id"] == request.user.id:
            me = item

    if request.user.is_authenticated and me is None:
        mine = qs.filter(user=request.user).aggregate(m=Max("points"))["m"]
        if mine:
            ahead = qs.values("user_id").annotate(b=Max("points")).filter(b__gt=mine).count()
            name = (request.user.full_name or "").strip() or request.user.email.split("@")[0]
            me = {"rank": ahead + 1, "name": name, "points": mine}

    return Response({"game": game, "level": level, "top": out, "me": me})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_stats(request):
    st, _ = Stats.objects.get_or_create(user=request.user)
    return Response({
        "played": st.played, "won": st.won,
        "best_memory": st.best_memory, "best_tictac": st.best_tictac,
        "streak": st.current_streak, "longest_streak": st.longest_streak,
    })
