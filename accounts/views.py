import logging

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import emails
from .models import EmailCode, User
from .serializers import (
    ChangePasswordSerializer, CodeSerializer, EmailOnlySerializer,
    LoginSerializer, MeSerializer, RegisterSerializer, ResetConfirmSerializer,
)
from .throttles import (
    CodeCheckThrottle, CodeSendThrottle, LoginThrottle, RegisterThrottle,
)

log = logging.getLogger(__name__)

# Deliberately identical for "email exists" and "email does not exist".
# Telling the difference hands an attacker a list of real customers.
NEUTRAL_SENT = {"detail": "If that email is registered, we have sent a code."}


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _err(msg, code=status.HTTP_400_BAD_REQUEST, **extra):
    payload = {"detail": msg}
    payload.update(extra)
    return Response(payload, status=code)


def _code_error(key):
    if key == "expired":
        return _err("That code has expired. Ask for a new one.", code=status.HTTP_410_GONE)
    if key == "too_many_attempts":
        return _err("Too many wrong tries. Ask for a new code.",
                    code=status.HTTP_429_TOO_MANY_REQUESTS)
    if key.startswith("wrong_code"):
        left = key.split(":")[1] if ":" in key else "0"
        return _err("That code is not right.", tries_left=int(left))
    return _err("No active code. Ask for a new one.")


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
def register(request):
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data
    email = data["email"]
    ip = client_ip(request)

    existing = User.objects.filter(email=email).first()

    if existing:
        if existing.is_email_verified:
            # Real, confirmed account. Do not create anything and do not
            # confirm it exists: point them at login or password reset.
            return Response(NEUTRAL_SENT, status=status.HTTP_200_OK)
        # Unverified signup being retried. Safe to refresh the password,
        # because nobody has proven ownership of this inbox yet.
        existing.set_password(data["password"])
        existing.full_name = data.get("full_name") or existing.full_name
        existing.phone = data.get("phone") or existing.phone
        existing.save(update_fields=["password", "full_name", "phone"])
        user = existing
    else:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=data["password"],
                full_name=data.get("full_name", ""),
                phone=data.get("phone", ""),
                preferred_lang=data.get("preferred_lang", "en"),
                signup_ip=ip,
                birth_day=data.get("birth_day") or None,
                birth_month=data.get("birth_month") or None,
            )

    _, raw = EmailCode.issue(user, EmailCode.VERIFY, ip=ip)
    emails.send_verify_code(user, raw, EmailCode.TTL_MINUTES)
    return Response(NEUTRAL_SENT, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([CodeCheckThrottle])
def verify_email(request):
    ser = CodeSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    user = User.objects.filter(email=ser.validated_data["email"]).first()
    if not user:
        # Same shape and status as a wrong code, so nothing is learned here.
        return _err("That code is not right.", tries_left=0)

    if user.is_email_verified:
        return Response({"detail": "Already confirmed. You can log in."})

    ok, key = EmailCode.verify(user, EmailCode.VERIFY, ser.validated_data["code"])
    if not ok:
        return _code_error(key)

    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    login(request, user)
    request.session.cycle_key()
    user.last_login_ip = client_ip(request)
    user.save(update_fields=["last_login_ip"])

    from django.utils import timezone
    today = timezone.localdate()
    birthday = bool(user.birth_day and user.birth_month
                    and user.birth_day == today.day and user.birth_month == today.month)

    return Response({
        "detail": "Email confirmed.",
        "user": MeSerializer(user).data,
        "birthday_today": birthday,
        "zodiac": zodiac_sign(user.birth_day, user.birth_month),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([CodeSendThrottle])
def resend_verify(request):
    ser = EmailOnlySerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    user = User.objects.filter(email=ser.validated_data["email"]).first()
    if user and not user.is_email_verified:
        allowed, wait = EmailCode.can_resend(user, EmailCode.VERIFY)
        if not allowed:
            return _err("Wait %d seconds before asking for another code." % wait,
                        code=status.HTTP_429_TOO_MANY_REQUESTS, retry_after=wait)
        _, raw = EmailCode.issue(user, EmailCode.VERIFY, ip=client_ip(request))
        emails.send_verify_code(user, raw, EmailCode.TTL_MINUTES)

    return Response(NEUTRAL_SENT)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login_view(request):
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    email = ser.validated_data["email"]

    user = authenticate(request, username=email, password=ser.validated_data["password"])
    if user is None:
        # One message for "no such email" and "wrong password".
        return _err("Email or password is not right.", code=status.HTTP_401_UNAUTHORIZED)

    if user.is_blocked:
        log.warning("Blocked user attempted login: %s", email)
        return _err("This account is on hold. Contact support.",
                    code=status.HTTP_403_FORBIDDEN)

    if not user.is_email_verified:
        return Response({
            "detail": "Confirm your email before logging in.",
            "needs_verification": True,
            "email": user.email,
        }, status=status.HTTP_403_FORBIDDEN)

    login(request, user)
    request.session.cycle_key()
    user.last_login_ip = client_ip(request)
    user.save(update_fields=["last_login_ip"])

    from django.utils import timezone
    today = timezone.localdate()
    birthday = bool(user.birth_day and user.birth_month
                    and user.birth_day == today.day and user.birth_month == today.month)

    return Response({"detail": "Logged in.", "user": MeSerializer(user).data,
                     "birthday_today": birthday})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"detail": "Logged out."})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([CodeSendThrottle])
def forgot_password(request):
    ser = EmailOnlySerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    user = User.objects.filter(email=ser.validated_data["email"]).first()
    if user and user.is_active and not user.is_blocked:
        allowed, wait = EmailCode.can_resend(user, EmailCode.RESET)
        if not allowed:
            return _err("Wait %d seconds before asking for another code." % wait,
                        code=status.HTTP_429_TOO_MANY_REQUESTS, retry_after=wait)
        _, raw = EmailCode.issue(user, EmailCode.RESET, ip=client_ip(request))
        emails.send_reset_code(user, raw, EmailCode.TTL_MINUTES)

    return Response(NEUTRAL_SENT)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([CodeCheckThrottle])
def reset_password(request):
    ser = ResetConfirmSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    user = User.objects.filter(email=ser.validated_data["email"]).first()
    if not user:
        return _err("That code is not right.", tries_left=0)

    ok, key = EmailCode.verify(user, EmailCode.RESET, ser.validated_data["code"])
    if not ok:
        return _code_error(key)

    with transaction.atomic():
        user.set_password(ser.validated_data["new_password"])
        # Receiving the code proves control of the inbox, which is exactly
        # what verification tests.
        user.is_email_verified = True
        user.save(update_fields=["password", "is_email_verified"])
        EmailCode.objects.filter(user=user, purpose=EmailCode.RESET,
                                 used_at__isnull=True).update(used_at=timezone.now())

    emails.send_password_changed(user)
    return Response({"detail": "Password changed. You can log in now."})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == "PATCH":
        ser = MeSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)
    return Response(MeSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    ser = ChangePasswordSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    if not request.user.check_password(ser.validated_data["current_password"]):
        return _err("Current password is not right.", code=status.HTTP_401_UNAUTHORIZED)

    request.user.set_password(ser.validated_data["new_password"])
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)

    emails.send_password_changed(request.user)
    return Response({"detail": "Password changed."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([LoginThrottle])
def delete_account(request):
    """
    Permanently deletes the account.

    Certificates go with it. That is deliberate and the UI says so plainly:
    a certificate carries the holder's name, so keeping it after they asked to
    be deleted would defeat the point of deleting them. Anyone holding a
    verification link will find it stops working - which is the honest
    outcome, not a bug.

    Password is required. Without it, one borrowed unlocked phone is enough to
    wipe somebody's account.
    """
    password = request.data.get("password") or ""
    if not request.user.check_password(password):
        return _err("Password is not right.", code=status.HTTP_401_UNAUTHORIZED)

    if request.data.get("confirm") != "DELETE":
        return _err("Type DELETE to confirm.")

    email = request.user.email
    log.warning("Account deleted: %s from %s", email, client_ip(request))

    user = request.user
    logout(request)
    user.delete()

    return Response({"detail": "Your account and all its data have been deleted."})


# Filled in by the install script from whatever is on disk, so adding a
# picture is a matter of dropping a file in and re-running it.
AVATAR_KEYS = [{"key": "free1", "file": "free1.jpeg"}, {"key": "free2", "file": "free2.jpeg"}, {"key": "free3", "file": "free3.jpeg"}, {"key": "free4", "file": "free4.jpeg"}, {"key": "free5", "file": "free5.jpeg"}, {"key": "free6", "file": "free6.jpeg"}, {"key": "free7", "file": "free7.jpeg"}, {"key": "free8", "file": "free8.jpeg"}, {"key": "free9", "file": "free9.jpeg"}, {"key": "paid1", "file": "paid1.jpeg"}, {"key": "paid10", "file": "paid10.jpeg"}, {"key": "paid11", "file": "paid11.jpeg"}, {"key": "paid12", "file": "paid12.jpeg"}, {"key": "paid13", "file": "paid13.jpeg"}, {"key": "paid14", "file": "paid14.jpeg"}, {"key": "paid15", "file": "paid15.jpeg"}, {"key": "paid16", "file": "paid16.jpeg"}, {"key": "paid17", "file": "paid17.jpeg"}, {"key": "paid18", "file": "paid18.jpeg"}, {"key": "paid19", "file": "paid19.jpeg"}, {"key": "paid2", "file": "paid2.jpeg"}, {"key": "paid20", "file": "paid20.jpeg"}, {"key": "paid21", "file": "paid21.jpeg"}, {"key": "paid22", "file": "paid22.jpeg"}, {"key": "paid23", "file": "paid23.jpeg"}, {"key": "paid3", "file": "paid3.jpeg"}, {"key": "paid4", "file": "paid4.jpeg"}, {"key": "paid5", "file": "paid5.jpeg"}, {"key": "paid6", "file": "paid6.jpeg"}, {"key": "paid7", "file": "paid7.jpeg"}, {"key": "paid8", "file": "paid8.jpeg"}, {"key": "paid9", "file": "paid9.jpeg"}]


@api_view(["GET"])
@permission_classes([AllowAny])
def avatars(request):
    return Response({"avatars": AVATAR_KEYS, "base": "/brand/avatars/"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_avatar(request):
    key = str(request.data.get("avatar") or "").strip()[:32]
    # Only keys we actually ship are accepted; anything else would let a user
    # store an arbitrary string that later gets pasted into an img src.
    if key and key not in [a["key"] for a in AVATAR_KEYS]:
        return _err("Unknown avatar.")
    request.user.avatar = key
    request.user.save(update_fields=["avatar"])
    return Response({"avatar": key})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_privacy(request):
    request.user.hide_from_leaderboard = bool(request.data.get("hide_from_leaderboard"))
    request.user.save(update_fields=["hide_from_leaderboard"])
    return Response({"hide_from_leaderboard": request.user.hide_from_leaderboard})


# Sun-sign date ranges. Sources differ by a day at the boundaries; these are
# the common western ones and match what PenFlow already showed.
ZODIAC_RANGES = [
    ("Capricorn", (12, 22), (1, 19)), ("Aquarius", (1, 20), (2, 18)),
    ("Pisces", (2, 19), (3, 20)),     ("Aries", (3, 21), (4, 19)),
    ("Taurus", (4, 20), (5, 20)),     ("Gemini", (5, 21), (6, 20)),
    ("Cancer", (6, 21), (7, 22)),     ("Leo", (7, 23), (8, 22)),
    ("Virgo", (8, 23), (9, 22)),      ("Libra", (9, 23), (10, 22)),
    ("Scorpio", (10, 23), (11, 21)),  ("Sagittarius", (11, 22), (12, 21)),
]


def zodiac_sign(day, month):
    """Arithmetic on a date. It says which sign a birthday falls in, and
    claims nothing beyond that."""
    if not day or not month:
        return None
    for name, (sm, sd), (em, ed) in ZODIAC_RANGES:
        if sm > em:                       # Capricorn wraps the year end
            if (month == sm and day >= sd) or (month == em and day <= ed):
                return name
        elif (month == sm and day >= sd) or (month == em and day <= ed):
            return name
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_card(request):
    from django.utils import timezone
    u = request.user
    today = timezone.localdate()

    is_birthday = bool(u.birth_day and u.birth_month
                       and u.birth_day == today.day and u.birth_month == today.month)
    turning = today.year - u.birth_year if (is_birthday and u.birth_year) else None

    return Response({
        "name": (u.full_name or "").strip() or u.email.split("@")[0],
        "email": u.email,
        "avatar": u.avatar,
        "zodiac": zodiac_sign(u.birth_day, u.birth_month),
        "birthday_today": is_birthday,
        "turning": turning,
        "has_birthday": bool(u.birth_day and u.birth_month),
        "show_birthday": u.show_birthday,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_birthday(request):
    """body: { day, month, year (optional), show }"""
    d = request.data
    if d.get("clear"):
        request.user.birth_day = request.user.birth_month = request.user.birth_year = None
        request.user.show_birthday = False
        request.user.save(update_fields=["birth_day", "birth_month", "birth_year", "show_birthday"])
        return Response({"detail": "Removed."})

    try:
        day, month = int(d.get("day")), int(d.get("month"))
    except (TypeError, ValueError):
        return _err("Pick a day and a month.")
    if not (1 <= month <= 12):
        return _err("Pick a month.")
    days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if not (1 <= day <= days):
        return _err("That month does not have %d days." % day)

    year = d.get("year")
    if year in ("", None):
        year = None
    else:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return _err("Year: four digits, or leave it blank.")
        from django.utils import timezone
        if not (1900 <= year <= timezone.localdate().year):
            return _err("Year: between 1900 and this year, or leave it blank.")

    request.user.birth_day = day
    request.user.birth_month = month
    request.user.birth_year = year
    request.user.show_birthday = bool(d.get("show"))
    request.user.save(update_fields=["birth_day", "birth_month", "birth_year", "show_birthday"])
    return Response({"day": day, "month": month, "year": year,
                     "zodiac": zodiac_sign(day, month),
                     "show_birthday": request.user.show_birthday})
