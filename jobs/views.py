"""Jobs: anyone signed in can post a job; members apply with their Connect profile ("easy apply");
the poster shortlists or turns people down, and shortlisting opens a chat between the two.
Everything is free - posting, applying, hiring. A job that asks applicants for money breaks the rules."""
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import Application, Job, JobReport

PAGE = 20
JOBS_PER_DAY = 5
MAX_DAYS = 90


class _UserThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class PostThrottle(_UserThrottle):
    scope = "jobs_post"


class ApplyThrottle(_UserThrottle):
    scope = "jobs_apply"


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


def _mod(u):
    return bool(u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_moderator", False)))


def _txt(v, n):
    return str(v or "").strip()[:n]


def _person(u):
    """The Connect profile that goes with an application."""
    from network.models import ProProfile
    from network.views import _av, _name, _ticked
    p = ProProfile.objects.filter(user=u).first()
    out = {"id": u.pk, "name": _name(u), "avatar_url": _av(u), "slug": None, "headline": "", "city": "",
           "country": (getattr(u, "signup_country", "") or "").upper(), "skills": [], "open_to_work": False, "verified": False}
    if p:
        out.update({"slug": p.slug, "headline": p.headline, "city": getattr(p, "city", ""), "verified": _ticked(p),
                    "country": (getattr(p, "country", "") or out["country"]).upper(),
                    "open_to_work": bool(getattr(p, "open_to_work", False))})
        try:
            out["skills"] = list(p.skills.values_list("name", flat=True)[:12])
        except Exception:
            pass
    return out


def _out(j, u, mine=None):
    from network.views import _name
    return {"id": j.id, "title": j.title, "company": j.company, "country": j.country, "state": j.state, "city": j.city,
            "workplace": j.workplace, "workplace_label": dict(Job.WORKPLACE)[j.workplace],
            "kind": j.kind, "kind_label": dict(Job.KIND)[j.kind],
            "salary": ({"min": j.salary_min, "max": j.salary_max, "currency": j.currency, "period": j.salary_period,
                        "period_label": dict(Job.PERIOD)[j.salary_period]} if j.show_salary and (j.salary_min or j.salary_max) else None),
            "description": j.description, "skills": j.skills or [], "deadline": j.deadline.isoformat(),
            "open": j.is_open, "closed": j.closed, "hidden": j.hidden, "applicants": j.applicants_count,
            "posted": j.created_at.strftime("%d %b %Y"), "posted_iso": j.created_at.isoformat(),
            "poster": {"name": _name(j.poster)},
            "is_mine": u.is_authenticated and u.pk == j.poster_id, "can_moderate": _mod(u),
            "my_application": mine}


def _clean(d, job=None):
    """Checks and tidies a job from the form. Returns (fields, error)."""
    f = {}
    f["title"] = _txt(d.get("title"), 120)
    f["company"] = _txt(d.get("company"), 120)
    f["description"] = _txt(d.get("description"), 6000)
    if len(f["title"]) < 3 or len(f["company"]) < 2:
        return None, "Add the job title and the company or shop name."
    if len(f["description"]) < 30:
        return None, "Describe the job in a few lines (at least 30 letters)."
    cc = _txt(d.get("country"), 2).upper()
    f["country"] = cc if len(cc) == 2 and cc.isalpha() else ""
    f["state"], f["city"] = _txt(d.get("state"), 100), _txt(d.get("city"), 100)
    f["workplace"] = d.get("workplace") if d.get("workplace") in dict(Job.WORKPLACE) else "onsite"
    f["kind"] = d.get("kind") if d.get("kind") in dict(Job.KIND) else "full_time"
    if f["workplace"] != "remote" and not f["city"]:
        return None, "Pick the city, or mark the job as remote."
    for k in ("salary_min", "salary_max"):
        try:
            v = int(d.get(k)) if str(d.get(k) or "").strip() else None
        except (TypeError, ValueError):
            return None, "Salary must be a number."
        f[k] = v if v is None or 0 <= v <= 1000000000 else None
    if f["salary_min"] and f["salary_max"] and f["salary_min"] > f["salary_max"]:
        f["salary_min"], f["salary_max"] = f["salary_max"], f["salary_min"]
    f["currency"] = (_txt(d.get("currency"), 6) or "PKR").upper()
    f["salary_period"] = d.get("salary_period") if d.get("salary_period") in dict(Job.PERIOD) else "month"
    f["show_salary"] = str(d.get("show_salary", True)).lower() not in ("false", "0", "")
    skills = d.get("skills") or []
    if isinstance(skills, str):
        skills = [s for s in skills.split(",")]
    f["skills"] = list(dict.fromkeys(_txt(s, 40) for s in skills if _txt(s, 40)))[:15]
    today = timezone.localdate()
    try:
        dl = timezone.datetime.strptime(str(d.get("deadline") or ""), "%Y-%m-%d").date()
    except ValueError:
        dl = today + timedelta(days=30)
    if dl < today:
        return None, "The last date to apply has already passed."
    f["deadline"] = min(dl, today + timedelta(days=MAX_DAYS))
    return f, None


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def jobs(request):
    u = request.user
    if request.method == "GET":
        qs = Job.objects.select_related("poster").filter(closed=False, hidden=False, deadline__gte=timezone.localdate())
        g = request.GET
        q = _txt(g.get("q"), 80)
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(company__icontains=q) | Q(description__icontains=q) | Q(city__icontains=q))
        if g.get("country"):
            qs = qs.filter(Q(country=_txt(g.get("country"), 2).upper()) | Q(workplace="remote"))
        if g.get("city"):
            qs = qs.filter(Q(city__iexact=_txt(g.get("city"), 100)) | Q(workplace="remote"))
        if g.get("workplace") in dict(Job.WORKPLACE):
            qs = qs.filter(workplace=g.get("workplace"))
        if g.get("kind") in dict(Job.KIND):
            qs = qs.filter(kind=g.get("kind"))
        skill = _txt(g.get("skill"), 40)
        if skill:
            qs = qs.filter(skills__icontains=skill)
        try:
            before = int(g.get("before") or 0)
        except ValueError:
            before = 0
        if before:
            qs = qs.filter(id__lt=before)
        rows = list(qs.order_by("-id")[:PAGE + 1])
        mine = {}
        if u.is_authenticated:
            mine = dict(Application.objects.filter(applicant=u, job_id__in=[j.id for j in rows]).values_list("job_id", "status"))
        return Response({"jobs": [_out(j, u, mine.get(j.id)) for j in rows[:PAGE]], "more": len(rows) > PAGE})

    if not u.is_authenticated:
        return _err("Sign in to post a job.", status.HTTP_401_UNAUTHORIZED)
    if getattr(u, "is_blocked", False) or not getattr(u, "is_email_verified", True):
        return _err("Verify your email before posting a job.", status.HTTP_403_FORBIDDEN)
    if not PostThrottle().allow_request(request, None):
        return _err("You are posting too fast. Try again later.", status.HTTP_429_TOO_MANY_REQUESTS)
    if Job.objects.filter(poster=u, created_at__date=timezone.localdate()).count() >= JOBS_PER_DAY:
        return _err("You can post %d jobs a day." % JOBS_PER_DAY)
    f, e = _clean(request.data)
    if e:
        return _err(e)
    j = Job.objects.create(poster=u, **f)
    return Response({"job": _out(j, u)}, status=status.HTTP_201_CREATED)


def _get(pk, u):
    j = Job.objects.select_related("poster").filter(id=pk).first()
    if not j:
        return None
    if j.hidden and not (_mod(u) or (u.is_authenticated and u.pk == j.poster_id)):
        return None
    return j


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def job_detail(request, pk):
    u = request.user
    j = _get(pk, u)
    if not j:
        return _err("This job is not available.", status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        mine = Application.objects.filter(job=j, applicant=u).values_list("status", flat=True).first() if u.is_authenticated else None
        return Response({"job": _out(j, u, mine)})
    if not u.is_authenticated:
        return _err("Sign in first.", status.HTTP_401_UNAUTHORIZED)
    if request.method == "DELETE":
        if u.pk != j.poster_id and not _mod(u):
            return _err("Not yours.", status.HTTP_403_FORBIDDEN)
        j.delete()
        return Response({"deleted": True})
    d = request.data
    if "hidden" in d:
        if not _mod(u):
            return _err("Only moderators can hide jobs.", status.HTTP_403_FORBIDDEN)
        j.hidden = bool(d.get("hidden"))
        j.save(update_fields=["hidden"])
        return Response({"job": _out(j, u)})
    if u.pk != j.poster_id:
        return _err("Not yours.", status.HTTP_403_FORBIDDEN)
    if "closed" in d and len(d) == 1:
        j.closed = bool(d.get("closed"))
        j.save(update_fields=["closed"])
        return Response({"job": _out(j, u)})
    f, e = _clean(d, j)
    if e:
        return _err(e)
    for k, v in f.items():
        setattr(j, k, v)
    j.save()
    return Response({"job": _out(j, u)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ApplyThrottle])
def apply(request, pk):
    u = request.user
    j = _get(pk, u)
    if not j or not j.is_open:
        return _err("This job is no longer taking applications.", status.HTTP_404_NOT_FOUND)
    if j.poster_id == u.pk:
        return _err("This is your own job.")
    from network.models import ProProfile
    p = ProProfile.objects.filter(user=u).first()
    if not p or not (p.headline or "").strip():
        return _err("Add a headline to your professional profile first - it is what the employer sees.")
    app, created = Application.objects.get_or_create(job=j, applicant=u, defaults={"note": _txt(request.data.get("note"), 1000)})
    if not created:
        if app.status != "withdrawn":
            return _err("You have already applied.")
        app.status, app.note = "applied", _txt(request.data.get("note"), 1000)
        app.save(update_fields=["status", "note", "updated_at"])
    Job.objects.filter(id=j.id).update(applicants_count=F("applicants_count") + 1)
    from network.views import _name
    from notifications.views import notify
    notify(j.poster, "job", "%s applied for %s." % (_name(u), j.title), "/job/%d" % j.id)
    return Response({"status": "applied"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request, pk):
    app = Application.objects.filter(job_id=pk, applicant=request.user).exclude(status="withdrawn").first()
    if not app:
        return _err("No application to withdraw.")
    app.status = "withdrawn"
    app.save(update_fields=["status", "updated_at"])
    Job.objects.filter(id=pk, applicants_count__gt=0).update(applicants_count=F("applicants_count") - 1)
    return Response({"status": "withdrawn"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def applicants(request, pk):
    j = Job.objects.filter(id=pk).first()
    if not j or (request.user.pk != j.poster_id and not _mod(request.user)):
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    rows = Application.objects.filter(job=j).exclude(status="withdrawn").select_related("applicant")
    return Response({"applicants": [{"id": a.id, "status": a.status, "note": a.note, "when": a.created_at.strftime("%d %b"),
                                     "person": _person(a.applicant)} for a in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_status(request, pk):
    """body: { status: "shortlisted" | "rejected" | "applied" } - by the poster. Shortlisting opens a chat."""
    a = Application.objects.select_related("job", "applicant").filter(id=pk).first()
    if not a or a.job.poster_id != request.user.pk:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    st = request.data.get("status")
    if st not in ("shortlisted", "rejected", "applied") or a.status == "withdrawn":
        return _err("Pick shortlist or not selected.")
    a.status = st
    a.save(update_fields=["status", "updated_at"])
    from network.views import _name
    from notifications.views import notify, open_thread
    thread = None
    if st == "shortlisted":
        thread = open_thread("job", a.id, request.user, a.applicant).id
        notify(a.applicant, "job", "Good news: %s shortlisted you for %s. You can chat now." % (_name(request.user), a.job.title), "/chat/%d" % thread)
    elif st == "rejected":
        notify(a.applicant, "job", "Your application for %s was not selected this time." % a.job.title, "/jobs?tab=applied")
    return Response({"status": st, "chat": thread})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_jobs(request):
    rows = Job.objects.filter(poster=request.user).select_related("poster")
    return Response({"jobs": [_out(j, request.user) for j in rows[:100]]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_applications(request):
    rows = Application.objects.filter(applicant=request.user).select_related("job", "job__poster")[:100]
    return Response({"applications": [{"id": a.id, "status": a.status, "status_label": dict(Application.STATUS)[a.status],
                                       "when": a.created_at.strftime("%d %b %Y"), "job": _out(a.job, request.user, a.status)} for a in rows]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def for_me(request):
    """Open jobs that ask for skills on my profile."""
    from network.models import ProProfile
    p = ProProfile.objects.filter(user=request.user).first()
    try:
        mine = [s.lower() for s in p.skills.values_list("name", flat=True)] if p else []
    except Exception:
        mine = []
    if not mine:
        return Response({"jobs": [], "skills": []})
    qs = Job.objects.select_related("poster").filter(closed=False, hidden=False, deadline__gte=timezone.localdate()).exclude(poster=request.user)
    out = []
    for j in qs.order_by("-id")[:300]:
        hit = [s for s in (j.skills or []) if s.lower() in mine]
        if hit:
            out.append((len(hit), j))
    out.sort(key=lambda x: (-x[0], -x[1].id))
    return Response({"jobs": [_out(j, request.user) for _, j in out[:PAGE]], "skills": mine})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ApplyThrottle])
def report(request, pk):
    j = _get(pk, request.user)
    if not j:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    reason = request.data.get("reason")
    if reason not in dict(JobReport.REASONS):
        return _err("Pick a reason.")
    JobReport.objects.create(job=j, reporter=request.user, reason=reason, note=_txt(request.data.get("note"), 500))
    from notifications.views import notify_admins
    notify_admins("report", "A job was reported (%s): %s" % (reason, j.title), "/admin/jobs/jobreport/")
    return Response({"ok": True})
