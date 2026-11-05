"""Wires the paid-course rules into the existing academy and shop code without editing their files (setup_academy_pay_v1)."""
import json
import logging

log = logging.getLogger(__name__)
DONE = {"v": False}


def _course_from(request, kw):
    from academy.models import Course
    slug = kw.get("slug")
    if not slug:
        try:
            slug = (json.loads(request.body or b"{}") or {}).get("course")
        except Exception:  # noqa: BLE001
            slug = request.POST.get("course")
    return Course.objects.filter(slug=str(slug or "")).first()


def _guard(view):
    from django.http import JsonResponse

    def inner(request, *a, **kw):
        from .access import can_open
        c = _course_from(request, kw)
        user = getattr(request, "user", None)
        if c is not None:
            if user is None or not user.is_authenticated:
                from django.contrib.auth import get_user
                user = get_user(request)
            if not can_open(user, c):
                return JsonResponse({"detail": "This course is locked. Buy it or use a coupon to open it.", "locked": True, "course": c.slug}, status=402)
        return view(request, *a, **kw)
    inner.__name__ = view.__name__
    inner.csrf_exempt = getattr(view, "csrf_exempt", False)
    return inner


def _courses_plus(view):
    def inner(request, *a, **kw):
        r = view(request, *a, **kw)
        try:
            from .access import open_ids, paywall
            from django.contrib.auth import get_user
            pw = paywall()
            if pw.on and isinstance(getattr(r, "data", None), dict):
                from shop.views import price
                ids = open_ids(get_user(request), pw)
                from academy.models import Course
                by_slug = dict(Course.objects.values_list("slug", "id"))
                for c in r.data.get("courses", []):
                    c["locked"] = by_slug.get(c.get("slug")) not in ids
                    c["price"] = price("course", "life")
                r.data["paywall"] = True
                r._is_rendered = False
                r.render()
        except Exception:  # noqa: BLE001
            log.exception("courses paywall info")
        return r
    inner.__name__ = view.__name__
    inner.csrf_exempt = getattr(view, "csrf_exempt", False)
    return inner


def install():
    if DONE["v"]:
        return
    DONE["v"] = True
    try:
        from shop import views as SV
        SV.CATALOG["course"] = {"name": "XpertAcademy course", "what": "Lifetime access to one XpertAcademy course, its quiz and certificate.",
                                "target": "course", "plans": {"life": ("lifetime", 4200, 0)}}
        prev = SV._target

        def _target(u, kind, tid):
            if kind == "course":
                from academy.models import Course
                from .access import can_open
                c = Course.objects.filter(pk=tid, is_active=True).first() if tid else None
                if not c:
                    return None, "Choose a course."
                if can_open(u, c):
                    return None, "This course is already open for you."
                return c.pk, c.title[:150]
            return prev(u, kind, tid)
        SV._target = _target
        # the course is bought from the academy page, not from /promote: hide it there, keep it in the price editor
        import threading
        flag = threading.local()
        cat0 = SV._catalog
        SV._catalog = lambda st: [x for x in cat0(st) if x["key"] != "course" or getattr(flag, "admin", False)]
        adm0 = SV.admin

        def admin(request, *a, **kw):
            flag.admin = True
            try:
                return adm0(request, *a, **kw)
            finally:
                flag.admin = False
        admin.csrf_exempt = getattr(adm0, "csrf_exempt", False)
        SV.admin = admin
    except Exception:  # noqa: BLE001
        log.exception("shop hook")
    try:
        from academy import views as AV
        for name in ("set_progress", "start_quiz", "submit_quiz"):
            setattr(AV, name, _guard(getattr(AV, name)))
        AV.courses = _courses_plus(AV.courses)
    except Exception:  # noqa: BLE001
        log.exception("academy hook")
