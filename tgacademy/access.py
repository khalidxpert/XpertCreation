"""Who may open a paid XpertAcademy course (setup_academy_pay_v1)."""
from django.utils import timezone

from .models import CouponUse, Enrollment, Paywall


def paywall():
    return Paywall.objects.first() or Paywall.objects.create()


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def open_ids(user, pw=None):
    """Set of course ids this member may open (only meaningful while the paywall is on)."""
    if not (user and user.is_authenticated):
        return set()
    from academy.models import Certificate, Course, LessonProgress
    pw = pw or paywall()
    if _staff(user):
        return set(Course.objects.values_list("id", flat=True))
    ids = set(LessonProgress.objects.filter(user=user, completed_at__lt=pw.started).values_list("lesson__course_id", flat=True))
    ids |= set(Certificate.objects.filter(user=user, revoked=False).values_list("course_id", flat=True))
    ids |= set(Enrollment.objects.filter(user=user).values_list("course_id", flat=True))
    ids |= set(CouponUse.objects.filter(user=user).values_list("course_id", flat=True))
    try:
        from shop.models import Order
        ids |= set(Order.objects.filter(user=user, product="course", status="paid").values_list("target_id", flat=True))
    except Exception:  # noqa: BLE001
        pass
    return ids


def can_open(user, course):
    pw = paywall()
    if not pw.on:
        return True
    return course.id in open_ids(user, pw)


def why(user, course):
    """Short reason a course is open (for the page)."""
    from academy.models import LessonProgress
    pw = paywall()
    if not pw.on:
        return "free"
    if _staff(user):
        return "staff"
    if LessonProgress.objects.filter(user=user, lesson__course=course, completed_at__lt=pw.started).exists():
        return "early"
    return "owned" if can_open(user, course) else ""


def now():
    return timezone.now()
