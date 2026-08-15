import base64
import io
import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import (
    Answer, Attempt, Certificate, Choice, Course, Lesson, LessonProgress, Question,
)


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")


class QuizThrottle(SimpleRateThrottle):
    """Bounds how fast someone can cycle attempts looking for an easy draw."""
    scope = "quiz"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class VerifyThrottle(SimpleRateThrottle):
    """Public endpoint. Stops serial numbers being enumerated."""
    scope = "verify"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


@api_view(["GET"])
@permission_classes([AllowAny])
def courses(request):
    """
    Course list with this user's progress folded in.

    Works signed out too - you just get zeroes, so the site stays browsable
    before anyone creates an account.
    """
    qs = Course.objects.filter(is_active=True).annotate(
        lesson_count=Count("lessons", distinct=True))

    done_map, certs = {}, {}
    if request.user.is_authenticated:
        rows = (LessonProgress.objects
                .filter(user=request.user, lesson__course__is_active=True)
                .values("lesson__course_id").annotate(n=Count("id")))
        done_map = {r["lesson__course_id"]: r["n"] for r in rows}
        certs = {c.course_id: c.serial for c in
                 Certificate.objects.filter(user=request.user, revoked=False)}

    out = []
    for c in qs:
        done = done_map.get(c.id, 0)
        pct = round(done / c.lesson_count * 100) if c.lesson_count else 0
        out.append({
            "slug": c.slug, "title": c.title, "icon": c.icon, "accent": c.accent,
            "blurb": c.blurb, "lesson_count": c.lesson_count, "lessons_done": done,
            "percent": pct,
            "quiz_unlocked": pct >= c.min_lessons_percent,
            "min_lessons_percent": c.min_lessons_percent,
            "pass_percent": c.pass_percent,
            "certificate_serial": certs.get(c.id),
        })
    return Response({"courses": out})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_progress(request):
    rows = (LessonProgress.objects.filter(user=request.user)
            .select_related("lesson", "lesson__course")
            .values_list("lesson__course__slug", "lesson__key"))
    data = {}
    for course_slug, key in rows:
        data.setdefault(course_slug, []).append(key)
    return Response({"progress": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_progress(request):
    """body: { course: "excel", lesson: "first-formula", done: true }"""
    course_slug = (request.data.get("course") or "").strip()
    lesson_key = (request.data.get("lesson") or "").strip()
    done = bool(request.data.get("done", True))

    lesson = Lesson.objects.filter(course__slug=course_slug, key=lesson_key,
                                   course__is_active=True).first()
    if not lesson:
        return Response({"detail": "Unknown lesson."}, status=status.HTTP_404_NOT_FOUND)

    if done:
        LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    else:
        LessonProgress.objects.filter(user=request.user, lesson=lesson).delete()

    total = Lesson.objects.filter(course=lesson.course).count()
    n = LessonProgress.objects.filter(user=request.user, lesson__course=lesson.course).count()
    pct = round(n / total * 100) if total else 0

    return Response({
        "course": course_slug, "lessons_done": n, "lesson_count": total,
        "percent": pct, "quiz_unlocked": pct >= lesson.course.min_lessons_percent,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([QuizThrottle])
def start_quiz(request, slug):
    course = Course.objects.filter(slug=slug, is_active=True).first()
    if not course:
        return Response({"detail": "Unknown course."}, status=status.HTTP_404_NOT_FOUND)

    if Certificate.objects.filter(user=request.user, course=course, revoked=False).exists():
        return Response({"detail": "You already hold a certificate for this course."},
                        status=status.HTTP_409_CONFLICT)

    total_lessons = Lesson.objects.filter(course=course).count()
    done = LessonProgress.objects.filter(user=request.user, lesson__course=course).count()
    pct = round(done / total_lessons * 100) if total_lessons else 0
    if pct < course.min_lessons_percent:
        return Response({"detail": "Finish %d%% of the lessons first." % course.min_lessons_percent,
                         "percent": pct, "needed": course.min_lessons_percent},
                        status=status.HTTP_403_FORBIDDEN)

    # Cooldown after a failure. Without it the quiz can be brute forced by
    # retaking until an easy combination comes up.
    last = Attempt.objects.filter(user=request.user, course=course,
                                  submitted_at__isnull=False).first()
    if last and not last.passed:
        ready = last.submitted_at + timedelta(minutes=Attempt.COOLDOWN_MINUTES)
        if timezone.now() < ready:
            wait = int((ready - timezone.now()).total_seconds() // 60) + 1
            return Response({"detail": "Try again in %d minutes." % wait,
                             "retry_in_minutes": wait},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

    pool = list(Question.objects.filter(course=course, is_active=True)
                .values_list("id", flat=True))
    if len(pool) < 3:
        return Response({"detail": "This quiz is not ready yet."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    chosen = random.sample(pool, min(course.quiz_questions, len(pool)))
    Attempt.objects.filter(user=request.user, course=course, submitted_at__isnull=True).delete()

    attempt = Attempt.objects.create(user=request.user, course=course,
                                     question_ids=chosen, total=len(chosen),
                                     ip=client_ip(request))

    questions = {q.id: q for q in
                 Question.objects.filter(id__in=chosen).prefetch_related("choices")}
    payload = []
    for qid in chosen:
        q = questions[qid]
        choices = list(q.choices.all())
        random.shuffle(choices)
        payload.append({
            "id": q.id, "text": q.text,
            # is_correct is deliberately absent. It never leaves the server.
            "choices": [{"id": ch.id, "text": ch.text} for ch in choices],
        })

    return Response({
        "attempt_id": attempt.id, "course": course.slug,
        "pass_percent": course.pass_percent,
        "expires_in_minutes": Attempt.EXPIRY_MINUTES,
        "questions": payload,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([QuizThrottle])
def submit_quiz(request, slug):
    """body: { attempt_id: 12, answers: { "<question_id>": <choice_id>, ... } }"""
    attempt = Attempt.objects.filter(
        id=request.data.get("attempt_id"), user=request.user,
        course__slug=slug, submitted_at__isnull=True).select_related("course").first()
    if not attempt:
        return Response({"detail": "No attempt in progress."},
                        status=status.HTTP_404_NOT_FOUND)

    if attempt.is_expired:
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=["submitted_at"])
        return Response({"detail": "That attempt timed out. Start a new one."},
                        status=status.HTTP_410_GONE)

    submitted = request.data.get("answers") or {}
    if not isinstance(submitted, dict):
        return Response({"detail": "answers must be an object."},
                        status=status.HTTP_400_BAD_REQUEST)

    allowed = set(attempt.question_ids)
    questions = {q.id: q for q in
                 Question.objects.filter(id__in=allowed).prefetch_related("choices")}

    score, review = 0, []
    with transaction.atomic():
        for qid in attempt.question_ids:
            q = questions.get(qid)
            if not q:
                continue
            raw = submitted.get(str(qid), submitted.get(qid))
            try:
                picked = int(raw)
            except (TypeError, ValueError):
                picked = None

            choices = list(q.choices.all())
            valid_ids = {c.id for c in choices}
            # A choice id belonging to a different question is not accepted.
            chosen = next((c for c in choices if c.id == picked), None) if picked in valid_ids else None
            correct = next((c for c in choices if c.is_correct), None)

            ok = bool(chosen and chosen.is_correct)
            if ok:
                score += 1

            Answer.objects.create(attempt=attempt, question=q, choice=chosen, was_correct=ok)
            review.append({
                "question_id": q.id, "text": q.text,
                "your_choice_id": chosen.id if chosen else None,
                "correct_choice_id": correct.id if correct else None,
                "was_correct": ok, "explanation": q.explanation,
            })

        attempt.score = score
        attempt.submitted_at = timezone.now()
        attempt.passed = attempt.percent >= attempt.course.pass_percent
        attempt.save(update_fields=["score", "submitted_at", "passed"])

        cert = None
        if attempt.passed:
            name = (request.user.full_name or "").strip() or request.user.email.split("@")[0]
            cert, _created = Certificate.objects.get_or_create(
                user=request.user, course=attempt.course,
                defaults={"attempt": attempt, "holder_name": name,
                          "course_title": attempt.course.title,
                          "score_percent": attempt.percent})

    return Response({
        "score": score, "total": attempt.total, "percent": attempt.percent,
        "pass_percent": attempt.course.pass_percent, "passed": attempt.passed,
        "certificate_serial": cert.serial if cert else None,
        "retry_in_minutes": None if attempt.passed else Attempt.COOLDOWN_MINUTES,
        "review": review,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_certificates(request):
    rows = Certificate.objects.filter(user=request.user, revoked=False)
    return Response({"certificates": [{
        "serial": c.serial, "course": c.course.slug, "course_title": c.course_title,
        "holder_name": c.holder_name, "score_percent": c.score_percent,
        "issued_at": c.issued_at.date().isoformat(),
    } for c in rows]})


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([VerifyThrottle])
def verify(request, serial):
    """
    Public check. Anybody holding the serial can confirm the certificate is
    real. Only what an employer needs is returned: no email, no user id.
    """
    cert = Certificate.objects.filter(serial=serial.upper().strip()).first()
    if not cert:
        return Response({"valid": False, "detail": "No certificate with that serial."},
                        status=status.HTTP_404_NOT_FOUND)
    if cert.revoked:
        return Response({"valid": False, "detail": "This certificate has been revoked.",
                         "serial": cert.serial})
    return Response({
        "valid": True, "serial": cert.serial, "holder_name": cert.holder_name,
        "course_title": cert.course_title, "score_percent": cert.score_percent,
        "issued_at": cert.issued_at.date().isoformat(),
    })


def _site_url():
    return getattr(settings, "SITE_URL", "https://learn.xpertcreation.com").rstrip("/")


def _qr_data_uri(text):
    """
    Inline QR as a data URI so the certificate is a single self-contained page.
    qrcode is optional: without it the serial still prints, just not scannable.
    """
    try:
        import qrcode
    except ImportError:
        return None
    try:
        qr = qrcode.QRCode(version=None, box_size=8, border=1,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#111827", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def certificate_page(request, serial):
    """
    Public, printable certificate. No login on purpose: the holder must be able
    to send the link to an employer who has no account.

    Revoked certificates are still served, marked VOID, rather than 404ing. A
    silent disappearance looks like a broken link; a visible VOID tells the
    reader what actually happened.
    """
    cert = Certificate.objects.filter(
        serial=serial.upper().strip()).select_related("course").first()
    if not cert:
        raise Http404("No certificate with that number.")

    verify_url = "%s/certificate/%s/" % (_site_url(), cert.serial)

    return render(request, "academy/certificate.html", {
        "cert": cert,
        "lesson_count": Lesson.objects.filter(course=cert.course).count(),
        "verify_url": verify_url,
        "qr_data_uri": _qr_data_uri(verify_url),
        "signature_url": getattr(settings, "CERTIFICATE_SIGNATURE_URL",
                                 "/brand/signature.jpg"),
        # Both images fail silently if missing, so the certificate still
        # prints correctly before the files are copied across.
        "logo_url": getattr(settings, "CERTIFICATE_LOGO_URL", "/brand/icon-192.png"),
    })


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([VerifyThrottle])
def learners(request):
    """
    Top learners: certificates first, then lessons completed.

    Anyone who opted out is still counted and still ranked - they simply are
    not named. Dropping them would quietly change everyone else's position.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    rows = (User.objects
            .filter(is_active=True, is_email_verified=True)
            .annotate(
                certs=Count("certificates", filter=Q(certificates__revoked=False), distinct=True),
                lessons=Count("lesson_progress", distinct=True))
            .filter(Q(certs__gt=0) | Q(lessons__gt=0))
            .order_by("-certs", "-lessons", "date_joined")[:50])

    total_lessons = Lesson.objects.filter(course__is_active=True).count()
    total_courses = Course.objects.filter(is_active=True).count()

    out, me = [], None
    for i, u in enumerate(rows, 1):
        anon = u.hide_from_leaderboard
        name = "Private learner" if anon else (
            (u.full_name or "").strip() or u.email.split("@")[0])
        item = {"rank": i, "name": name, "certificates": u.certs,
                "lessons": u.lessons, "anonymous": anon}
        out.append(item)
        if request.user.is_authenticated and u.id == request.user.id:
            me = dict(item, name=(u.full_name or "").strip() or u.email.split("@")[0])

    if request.user.is_authenticated and me is None:
        mine = (User.objects.filter(id=request.user.id)
                .annotate(certs=Count("certificates", filter=Q(certificates__revoked=False), distinct=True),
                          lessons=Count("lesson_progress", distinct=True)).first())
        if mine and (mine.certs or mine.lessons):
            ahead = (User.objects.filter(is_active=True, is_email_verified=True)
                     .annotate(c=Count("certificates", filter=Q(certificates__revoked=False), distinct=True),
                               l=Count("lesson_progress", distinct=True))
                     .filter(Q(c__gt=mine.certs) | Q(c=mine.certs, l__gt=mine.lessons)).count())
            me = {"rank": ahead + 1,
                  "name": (mine.full_name or "").strip() or mine.email.split("@")[0],
                  "certificates": mine.certs, "lessons": mine.lessons,
                  "anonymous": mine.hide_from_leaderboard}

    return Response({"top": out, "me": me,
                     "total_lessons": total_lessons, "total_courses": total_courses})
