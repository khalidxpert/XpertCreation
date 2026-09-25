import base64
import io
import random
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
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
    VideoPost, VideoVote,
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
            # A review of the course unlocks the certificate. Anyone who
            # reviewed it before passing is not asked twice.
            from reviews.models import Review as _Review
            reviewed = _Review.objects.filter(
                user=request.user, module="course",
                course=attempt.course.slug).exists()
            cert, _created = Certificate.objects.get_or_create(
                user=request.user, course=attempt.course,
                defaults={"attempt": attempt, "holder_name": name,
                          "course_title": attempt.course.title,
                          "score_percent": attempt.percent,
                          "review_ok": reviewed})

    return Response({
        "score": score, "total": attempt.total, "percent": attempt.percent,
        "pass_percent": attempt.course.pass_percent, "passed": attempt.passed,
        "certificate_serial": cert.serial if (cert and cert.review_ok) else None,
        "review_needed": bool(cert and not cert.review_ok),
        "review_course": attempt.course.slug,
        "retry_in_minutes": None if attempt.passed else Attempt.COOLDOWN_MINUTES,
        "review": review,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_certificates(request):
    rows = Certificate.objects.filter(user=request.user, revoked=False)
    return Response({"certificates": [{
        "serial": c.serial if c.review_ok else None,
        "review_needed": not c.review_ok,
        "course": c.course.slug, "course_title": c.course_title,
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
    # A certificate still waiting on its review is not issued yet.
    if not cert or not cert.review_ok:
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
    if not cert or not cert.review_ok:
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

# ------------------------------------------------------------------ videos
#
# Community video library. Anyone who has finished a course can add a
# link; a moderator decides whether it goes live; everyone else votes.

import re as _re

# What the embed needs, pulled out of whatever form of link was pasted.
# People paste watch links, share links, shorts links and sometimes the
# embed code itself, so all of them have to work.
_YT = [
    _re.compile(r"(?:youtube\.com/watch\?(?:.*&)?v=)([A-Za-z0-9_-]{11})"),
    _re.compile(r"(?:youtu\.be/)([A-Za-z0-9_-]{11})"),
    _re.compile(r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})"),
    _re.compile(r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})"),
    # Live streams and their recordings sit on a different path.
    _re.compile(r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})"),
    _re.compile(r"(?:youtube-nocookie\.com/embed/)([A-Za-z0-9_-]{11})"),
]
_VM = _re.compile(r"vimeo\.com/(?:video/)?(\d{6,12})")

MAX_PENDING = 3          # one person cannot flood the queue overnight


def _verr(msg, code=status.HTTP_400_BAD_REQUEST):
    """Short error reply for the video endpoints. The rest of this file
    writes these inline; this just saves repeating three lines sixteen
    times below."""
    return Response({"detail": msg}, status=code)


def _parse_video(url):
    """Give back (source, id) or (None, None). Only these two sites are
    accepted - anything else is a link we cannot embed or vouch for."""
    url = (url or "").strip()
    if not url:
        return None, None
    for rx in _YT:
        m = rx.search(url)
        if m:
            return VideoPost.YOUTUBE, m.group(1)
    m = _VM.search(url)
    if m:
        return VideoPost.VIMEO, m.group(1)
    # A bare 11-character id, since people paste those too
    if _re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return VideoPost.YOUTUBE, url
    return None, None


def _video_json(p, me=None, my_votes=None):
    mine = None
    if my_votes is not None:
        mine = my_votes.get(p.id)
    elif me is not None and me.is_authenticated:
        v = VideoVote.objects.filter(post=p, user=me).first()
        mine = v.value if v else None
    return {
        "id": p.id,
        "course": p.course,
        "title": p.title,
        "note": p.note,
        "source": p.source,
        "video_id": p.video_id,
        "embed": p.embed_url,
        "watch": p.watch_url,
        "thumb": p.thumb_url,
        "up": p.up,
        "down": p.down,
        "views": p.views,
        "my_vote": mine,
        "author": (p.author.full_name or p.author.email.split("@")[0]),
        "author_id": p.author_id,
        "state": p.state,
        "note_back": p.decision_note,
        "created_at": p.created_at.isoformat(),
    }


def _finished_any_course(user):
    """Has this person finished at least one course?

    Not gatekeeping for its own sake: a spammer will not sit through ten
    lessons, and a real learner has already done it without noticing.
    """
    try:
        from academy.models import Certificate
        if Certificate.objects.filter(user=user).exists():
            return True
    except Exception:
        pass
    try:
        # No "done" flag - a row here means that lesson was completed.
        # Five finished lessons is enough to show somebody is real.
        from academy.models import LessonProgress
        return LessonProgress.objects.filter(user=user).count() >= 5
    except Exception:
        return False


# ------------------------------------------------------------------ vetting
#
# Two checks before a submission reaches the queue. Neither replaces a
# moderator looking - they only cut the obvious cases so the queue stays
# short enough to read properly.

# Safe to find anywhere: no ordinary English word contains these.
_BAD_ANY = {
    "porn", "pornhub", "xvideos", "xnxx", "xhamster", "redtube", "hentai",
    "onlyfans", "camgirl", "masturbat", "blowjob", "creampie", "gangbang",
    "prostitut", "brothel", "bukkake", "cumshot", "deepthroat", "handjob",
    "nsfw", "bdsm", "fetish", "stripper",
}

# These must match a whole word. "Analysis" contains anal, "Essex"
# contains sex, "Dickens" contains dick - a filter that blocks those is
# worse than no filter at all.
_BAD_WORD = {
    "sex", "sexy", "sexual", "nude", "nudes", "naked", "xxx", "milf",
    "escort", "erotic", "erotica", "orgasm", "boobs", "tits", "dick",
    "penis", "vagina", "anal", "fuck", "fucking", "fucked", "slut",
    "whore",
}

# Letters swapped in to slip past. Folding them back catches the lazy.
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
                       "7": "t", "@": "a", "$": "s", "!": "i", "|": "i"})


def _looks_dirty(text):
    """True if the wording trips the list. A false positive only means a
    human looks at it, which was going to happen anyway."""
    if not text:
        return False
    flat = text.lower().translate(_LEET)
    if any(w in flat for w in _BAD_ANY):
        return True
    if set(_re.findall(r"[a-z]+", flat)) & _BAD_WORD:
        return True
    # "P O R N" and "p.o.r.n" fold to the same thing. Checked only
    # against the unambiguous list, because squashing "analysis of"
    # gives "analysisof", which contains anal.
    squashed = _re.sub(r"[^a-z]", "", flat)
    if len(squashed) <= 40 and any(w in squashed for w in _BAD_ANY):
        return True
    if len(squashed) <= 12 and squashed in _BAD_WORD:
        return True
    return False


def _real_title(source, vid):
    """Ask the site what the video is actually called.

    The word list only sees the title somebody typed. This sees the one
    the video really has - the difference between catching a clean title
    on a filthy video and not catching it.

    oEmbed needs no key and no quota. If it is slow or down we carry on;
    a moderator still has to look, so a missing check costs nothing.
    """
    import json as _json
    import urllib.request as _url

    if source == VideoPost.VIMEO:
        api = "https://vimeo.com/api/oembed.json?url=https://vimeo.com/%s" % vid
    else:
        api = ("https://www.youtube.com/oembed?format=json&url="
               "https://www.youtube.com/watch?v=%s" % vid)
    try:
        req = _url.Request(api, headers={"User-Agent": "XpertAcademy/1.0"})
        with _url.urlopen(req, timeout=6) as r:
            data = _json.loads(r.read().decode("utf-8", "replace"))
        return (data.get("title") or ""), (data.get("author_name") or "")
    except Exception:
        return None, None


@api_view(["GET"])
@permission_classes([AllowAny])
def videos_list(request):
    """Published videos for one course, best first."""
    course = str(request.GET.get("course") or "").strip()[:32]
    if not course:
        return _verr("Which course?")

    qs = VideoPost.objects.filter(course=course, state=VideoPost.LIVE)
    posts = list(qs.select_related("author")[:60])

    # One query for the reader's own votes rather than one per video
    my_votes = {}
    if request.user.is_authenticated and posts:
        for v in VideoVote.objects.filter(post__in=posts, user=request.user):
            my_votes[v.post_id] = v.value

    posts.sort(key=lambda p: (-p.score, -p.up, -p.created_at.timestamp()))

    # Each author's role, worked out once per author, not once per video
    from .badges import role_for as _role_for
    _roles = {}
    for p in posts:
        if p.author_id in _roles:
            continue
        try:
            ro = _role_for(_badge_stats(p.author))
            _roles[p.author_id] = {"key": ro["key"], "title": ro["title"],
                                   "icon": ro["icon"]}
        except Exception:
            _roles[p.author_id] = None
    return Response({
        "course": course,
        "count": len(posts),
        "videos": [dict(_video_json(p, my_votes=my_votes),
                        author_role=_roles.get(p.author_id)) for p in posts],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def videos_add(request):
    """body: { course, url, title, note }"""
    course = str(request.data.get("course") or "").strip()[:32]
    url = str(request.data.get("url") or "").strip()[:400]
    title = str(request.data.get("title") or "").strip()[:140]
    note = str(request.data.get("note") or "").strip()[:1000]

    if not course:
        return _verr("Which course is this for?")
    if not title:
        return _verr("Give it a title.")
    if len(title) < 6:
        return _verr("That title is too short to be useful.")

    source, vid = _parse_video(url)
    if not vid:
        return _verr("That link is not one we can show. YouTube or Vimeo only.")

    if _looks_dirty(title) or _looks_dirty(note):
        return _verr("That wording is not allowed here.")

    # The words somebody types are their own. This is what the
    # video is really called - the only check that catches a
    # clean title on a filthy video.
    real, channel = _real_title(source, vid)
    if real is None:
        return _verr("Could not reach that video. Check the link works.")
    if _looks_dirty(real) or _looks_dirty(channel):
        return _verr("That video is not suitable for this site.")

    if not _finished_any_course(request.user):
        return _verr("Finish one course first, then you can add to the library.",
                    status.HTTP_403_FORBIDDEN)

    pending = VideoPost.objects.filter(author=request.user,
                                       state=VideoPost.PENDING).count()
    if pending >= MAX_PENDING:
        return _verr("You have %d waiting to be checked. Wait for those "
                    "before adding more." % pending)

    # The same video twice in one course helps nobody
    dupe = VideoPost.objects.filter(course=course, video_id=vid).exclude(
        state=VideoPost.REJECTED).first()
    if dupe:
        return _verr("That video is already in this course.")

    p = VideoPost.objects.create(
        course=course, author=request.user, title=title, note=note,
        source=source, video_id=vid)

    return Response({"ok": True, "id": p.id,
                     "detail": "Thanks. A moderator will look at it shortly."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def videos_vote(request, pk):
    """body: { value: 1 | -1 | 0 }   0 takes the vote back."""
    p = VideoPost.objects.filter(pk=pk, state=VideoPost.LIVE).first()
    if not p:
        return _verr("No such video.", status.HTTP_404_NOT_FOUND)

    try:
        value = int(request.data.get("value"))
    except (TypeError, ValueError):
        return _verr("Helpful or not?")
    if value not in (1, -1, 0):
        return _verr("Helpful or not?")

    if p.author_id == request.user.id:
        return _verr("You cannot vote on your own.")

    existing = VideoVote.objects.filter(post=p, user=request.user).first()

    if value == 0:
        if existing:
            if existing.value == VideoVote.UP:
                p.up = max(0, p.up - 1)
            else:
                p.down = max(0, p.down - 1)
            existing.delete()
            p.save(update_fields=["up", "down"])
    elif existing:
        if existing.value != value:
            # Moved from one side to the other
            if value == VideoVote.UP:
                p.up += 1
                p.down = max(0, p.down - 1)
            else:
                p.down += 1
                p.up = max(0, p.up - 1)
            existing.value = value
            existing.save(update_fields=["value"])
            p.save(update_fields=["up", "down"])
    else:
        VideoVote.objects.create(post=p, user=request.user, value=value)
        if value == VideoVote.UP:
            p.up += 1
        else:
            p.down += 1
        p.save(update_fields=["up", "down"])

    p.refresh_from_db()
    return Response({"up": p.up, "down": p.down,
                     "my_vote": None if value == 0 else value})


@api_view(["POST"])
@permission_classes([AllowAny])
def videos_seen(request, pk):
    """Someone opened it. Counted loosely - this is a popularity hint,
    not an audited figure, so no attempt is made to stop repeats."""
    VideoPost.objects.filter(pk=pk, state=VideoPost.LIVE).update(
        views=models.F("views") + 1)
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def videos_mine(request):
    """What this person has submitted, whatever state it is in."""
    posts = VideoPost.objects.filter(author=request.user)[:50]
    return Response({"videos": [_video_json(p) for p in posts]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def videos_queue(request):
    """Waiting to be checked. Moderators only."""
    if not (request.user.is_moderator or request.user.is_staff):
        return _verr("Moderators only.", status.HTTP_403_FORBIDDEN)
    posts = VideoPost.objects.filter(state=VideoPost.PENDING
                                     ).select_related("author")[:100]
    return Response({"count": len(posts),
                     "videos": [_video_json(p) for p in posts]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def videos_decide(request, pk):
    """body: { action: "live" | "rejected", note }"""
    if not (request.user.is_moderator or request.user.is_staff):
        return _verr("Moderators only.", status.HTTP_403_FORBIDDEN)

    p = VideoPost.objects.filter(pk=pk).first()
    if not p:
        return _verr("No such video.", status.HTTP_404_NOT_FOUND)

    action = str(request.data.get("action") or "").strip()
    if action not in (VideoPost.LIVE, VideoPost.REJECTED):
        return _verr("Publish it or turn it down.")

    p.state = action
    p.decision_note = str(request.data.get("note") or "").strip()[:300]
    p.decided_by = request.user
    p.decided_at = timezone.now()
    p.save(update_fields=["state", "decision_note", "decided_by", "decided_at"])

    return Response({"ok": True, "state": p.state})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def videos_edit(request, pk):
    """body: { title, note }

    Only the person who sent it, and only while it is waiting. Letting
    the words change after a moderator published it would make the check
    meaningless.
    """
    p = VideoPost.objects.filter(pk=pk, author=request.user).first()
    if not p:
        return _verr("Not yours, or gone.", status.HTTP_404_NOT_FOUND)
    if p.state != VideoPost.PENDING:
        return _verr("That one has been looked at already. Send a new one "
                     "if it needs changing.")

    title = str(request.data.get("title") or "").strip()[:140]
    note = str(request.data.get("note") or "").strip()[:1000]
    if len(title) < 6:
        return _verr("That title is too short to be useful.")
    if _looks_dirty(title) or _looks_dirty(note):
        return _verr("That wording is not allowed here.")

    p.title = title
    p.note = note
    p.save(update_fields=["title", "note"])
    return Response({"ok": True, "video": _video_json(p)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def videos_delete(request, pk):
    """Take back something still waiting."""
    p = VideoPost.objects.filter(pk=pk, author=request.user).first()
    if not p:
        return _verr("Not yours, or gone.", status.HTTP_404_NOT_FOUND)
    if p.state != VideoPost.PENDING:
        return _verr("Only ones still waiting can be taken back.")
    p.delete()
    return Response({"ok": True})



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def course_review(request):
    """body: { course, stars, clarity, pace, comment }

    The review that unlocks a certificate. Only somebody who passed the
    course can send one, so every course rating comes from a learner who
    actually finished it.
    """
    from reviews.models import Review

    slug = str(request.data.get("course") or "").strip()[:32]
    cert = (Certificate.objects.filter(user=request.user, course__slug=slug,
                                       revoked=False)
            .select_related("course").first())
    if not cert:
        return Response({"detail": "Finish the course and pass its quiz first."},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        stars = int(request.data.get("stars"))
    except (TypeError, ValueError):
        stars = 0
    if stars < 1 or stars > 5:
        return Response({"detail": "Pick from one to five stars."},
                        status=status.HTTP_400_BAD_REQUEST)

    def small(key):
        try:
            v = int(request.data.get(key))
        except (TypeError, ValueError):
            return None
        return v if 1 <= v <= 3 else None

    comment = str(request.data.get("comment") or "").strip()[:600]
    dirty = globals().get("_looks_dirty")
    if comment and dirty and dirty(comment):
        return Response({"detail": "That wording is not allowed here."},
                        status=status.HTTP_400_BAD_REQUEST)

    r, _new = Review.objects.get_or_create(
        user=request.user, module="course", course=slug,
        defaults={"stars": stars})
    r.stars = stars
    r.clarity = small("clarity")
    r.pace = small("pace")
    r.comment = comment
    # Stars can carry nothing harmful, so they go up at once. Words wait.
    r.state = Review.PENDING if comment else Review.PUBLISHED
    r.save()

    if not cert.review_ok:
        cert.review_ok = True
        cert.save(update_fields=["review_ok"])

    return Response({"ok": True, "serial": cert.serial,
                     "course_title": cert.course_title,
                     "comment_pending": r.state == Review.PENDING})


# ------------------------------------------------------------------ badges

LANG_SLUGS = ("korean", "japanese", "turkish", "german", "french", "alquran")


def _badge_stats(user):
    """The numbers roles and medals are worked out from. Every one is
    something the person did - nothing counts time spent on a page."""
    from django.db.models import Sum
    from reviews.models import Review
    from .badges import best_streak

    days = []
    for tstamp in LessonProgress.objects.filter(user=user).values_list(
            "completed_at", flat=True):
        try:
            days.append(timezone.localtime(tstamp).date())
        except Exception:
            days.append(tstamp.date())

    good = Certificate.objects.filter(user=user, revoked=False, review_ok=True)
    live = VideoPost.objects.filter(author=user, state=VideoPost.LIVE)
    return {
        "lessons": len(days),
        "certs": good.count(),
        "streak": best_streak(days),
        "videos": live.count(),
        "helpful": live.aggregate(n=Sum("up"))["n"] or 0,
        "reviews": Review.objects.filter(user=user, module="course").count(),
        "polyglot": good.filter(course__slug__in=LANG_SLUGS).count(),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_badges(request):
    from .badges import summary
    s = _badge_stats(request.user)
    out = summary(s)
    out["stats"] = s
    # Send every step, not only the next one, so the page can show what
    # each medal takes rather than keeping it a secret.
    from .badges import FAMILIES
    steps = {f["id"]: f["steps"] for f in FAMILIES}
    for f in out["families"]:
        f["steps"] = steps.get(f["id"], [])
    return Response(out)


@api_view(["GET"])
@permission_classes([AllowAny])
def badge_board(request):
    """Who has collected the most medals.

    Worked out from the same numbers as everybody's own badge page, so
    nobody can be ahead by a rule that is not written down. Held for
    five minutes: a leaderboard that is five minutes old is fine, and
    rebuilding it on every visit is not.
    """
    from django.contrib.auth import get_user_model
    from django.core.cache import cache
    from reviews.models import Review
    from .badges import summary, best_streak

    ready = cache.get("xc_badge_board")
    if ready is not None:
        return Response(ready)

    lessons, days = {}, {}
    for uid, ts in LessonProgress.objects.values_list("user_id", "completed_at"):
        lessons[uid] = lessons.get(uid, 0) + 1
        try:
            d = timezone.localtime(ts).date()
        except Exception:
            d = ts.date()
        days.setdefault(uid, set()).add(d)

    certs, poly = {}, {}
    for uid, slug in Certificate.objects.filter(
            revoked=False, review_ok=True).values_list("user_id", "course__slug"):
        certs[uid] = certs.get(uid, 0) + 1
        if slug in LANG_SLUGS:
            poly[uid] = poly.get(uid, 0) + 1

    vids, helpful = {}, {}
    for uid, up in VideoPost.objects.filter(
            state=VideoPost.LIVE).values_list("author_id", "up"):
        vids[uid] = vids.get(uid, 0) + 1
        helpful[uid] = helpful.get(uid, 0) + (up or 0)

    revs = {}
    for uid in Review.objects.filter(module="course").values_list("user_id", flat=True):
        revs[uid] = revs.get(uid, 0) + 1

    rows = []
    for uid in set(lessons) | set(certs) | set(vids) | set(revs):
        s = {"lessons": lessons.get(uid, 0), "certs": certs.get(uid, 0),
             "streak": best_streak(days.get(uid, [])), "videos": vids.get(uid, 0),
             "helpful": helpful.get(uid, 0), "reviews": revs.get(uid, 0),
             "polyglot": poly.get(uid, 0)}
        rows.append((uid, summary(s), s))

    rows.sort(key=lambda x: (-x[1]["earned"], -x[2]["certs"], -x[2]["lessons"]))
    rows = rows[:20]

    people = {u.id: u for u in get_user_model().objects.filter(
        id__in=[r[0] for r in rows])}

    board = []
    for uid, r, s in rows:
        u = people.get(uid)
        if not u:
            continue
        # Anyone who asked to stay off the leaderboard keeps their place
        # but not their name.
        hide = getattr(u, "hide_from_leaderboard", False)
        board.append({
            "name": "Private" if hide
                    else ((u.full_name or "").strip() or u.email.split("@")[0]),
            "role": r["role"]["title"], "icon": r["role"]["icon"],
            "medals": r["earned"], "certs": s["certs"], "lessons": s["lessons"],
        })

    out = {"board": board}
    cache.set("xc_badge_board", out, 300)
    return Response(out)
