"""Blue tick KYC for members: /get-verified. Same private storage and review screen as companies."""
import os
import secrets

from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PersonDoc, PersonKyc
from .views import DOCS, MAGIC, PHONE, _err, _reviewer, _rm, _t


def _profile(u):
    try:
        from network.models import ProProfile
        return ProProfile.objects.filter(user=u).first()
    except Exception:
        return None


def _ticked(u):
    p = _profile(u)
    return bool((p and p.verified) or u.is_staff or u.is_superuser or getattr(u, "is_moderator", False))


def _out(k):
    p = _profile(k.user)
    return {"id": k.id, "whatsapp": k.whatsapp, "status": k.status, "status_label": dict(PersonKyc.STATES)[k.status], "review_note": k.review_note,
            "has_profile": bool(p), "profile_slug": p.slug if p else "", "ticked": _ticked(k.user),
            "docs": [{"id": d.id, "kind": d.kind, "kind_label": dict(PersonDoc.KINDS)[d.kind], "name": d.name, "size": d.size} for d in k.docs.order_by("id")]}


def wipe(k):
    for d in k.docs.all():
        _rm(d.path)
    k.docs.all().delete()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def me(request):
    k, _ = PersonKyc.objects.get_or_create(user=request.user)
    if request.method == "POST" and "whatsapp" in request.data:
        import re
        w = re.sub(r"[\s-]", "", _t(request.data.get("whatsapp"), 24))
        if w and not PHONE.match(w):
            return _err("Write the WhatsApp number like +923001234567.")
        k.whatsapp = w; k.save(update_fields=["whatsapp", "updated_at"])
    return Response(_out(k))


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def docs(request):
    k, _ = PersonKyc.objects.get_or_create(user=request.user)
    if k.status == PersonKyc.PENDING:
        return _err("Your documents are being reviewed.")
    if request.method == "DELETE":
        d = k.docs.filter(pk=request.data.get("doc")).first()
        if d: _rm(d.path); d.delete()
        return Response(_out(k))
    f = request.FILES.get("file"); kind = request.data.get("kind")
    if not f or kind not in dict(PersonDoc.KINDS):
        return _err("Choose the document type and a file.")
    if f.size > 5 * 1024 * 1024:
        return _err("That file is over 5 MB.")
    if k.docs.count() >= 6:
        return _err("You can upload up to 6 documents.")
    head = f.read(8); f.seek(0)
    ext = next((e for m, e in MAGIC if head.startswith(m)), None)
    if not ext:
        return _err("Use a PDF, JPG or PNG file.")
    rel = "p%d/%s.%s" % (k.user_id, secrets.token_hex(12), ext)
    full = os.path.join(DOCS, rel); os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as out:
        for ch in f.chunks():
            out.write(ch)
    os.chmod(full, 0o600)
    PersonDoc.objects.create(kyc=k, kind=kind, path=rel, name=_t(f.name, 120), size=f.size)
    return Response(_out(k))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit(request):
    k, _ = PersonKyc.objects.get_or_create(user=request.user)
    if not _profile(request.user):
        return _err("First create your XpertConnect profile - the blue tick shows on it.")
    if _ticked(request.user):
        return _err("You already have the blue tick.")
    if not PHONE.match(k.whatsapp or ""):
        return _err("Add your WhatsApp number - our team will contact you on it.")
    kinds = set(k.docs.values_list("kind", flat=True))
    if not ({"cnic_front", "cnic_back"} <= kinds or "passport" in kinds):
        return _err("Upload your CNIC (front and back) or your passport.")
    if "address" not in kinds:
        return _err("Upload an address proof (a utility bill or bank statement).")
    k.status, k.review_note = PersonKyc.PENDING, ""; k.save(update_fields=["status", "review_note", "updated_at"])
    try:
        from notifications.views import notify_admins
        notify_admins("kyc", "Blue tick KYC to review: %s" % (getattr(request.user, "full_name", "") or request.user.email), "/company-review")
    except Exception:
        pass
    return Response(_out(k))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def doc_file(request, doc):
    d = PersonDoc.objects.filter(pk=doc).select_related("kyc").first()
    if not d or not (d.kyc.user_id == request.user.id or _reviewer(request.user)):
        raise Http404
    full = os.path.join(DOCS, d.path)
    if not os.path.exists(full):
        raise Http404
    try:
        from auditlog.models import AuditEvent
        AuditEvent.objects.create(user=request.user, action="kyc_doc_view", target="person %d doc %d" % (d.kyc.user_id, d.id))
    except Exception:
        pass
    r = FileResponse(open(full, "rb"), as_attachment=False, filename=d.name or os.path.basename(full))
    r["X-Content-Type-Options"] = "nosniff"; r["Cache-Control"] = "private, no-store"
    return r


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def review_list(request):
    if not _reviewer(request.user):
        return _err("Moderators only.", 403)
    def one(k):
        d = _out(k); d["name"] = getattr(k.user, "full_name", "") or k.user.email; d["email"] = k.user.email
        return d
    return Response({"pending": [one(k) for k in PersonKyc.objects.filter(status=PersonKyc.PENDING).select_related("user").order_by("updated_at")],
                     "recent": [one(k) for k in PersonKyc.objects.filter(status__in=[PersonKyc.APPROVED, PersonKyc.REJECTED]).select_related("user").order_by("-reviewed_at")[:20]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review(request, pk):
    if not _reviewer(request.user):
        return _err("Moderators only.", 403)
    k = PersonKyc.objects.filter(pk=pk).select_related("user").first()
    act = request.data.get("action")
    if not k or act not in ("approve", "reject"):
        return _err("Choose approve or reject.")
    note = _t(request.data.get("note"), 500)
    if act == "reject" and not note:
        return _err("Write the reason, so the member knows what to fix.")
    p = _profile(k.user)
    if act == "approve":
        if not p:
            return _err("This member has no XpertConnect profile yet.")
        upd = {"verified": True}
        if "verified_at" in {f.name for f in p._meta.get_fields()}:
            upd["verified_at"] = timezone.now()
        type(p).objects.filter(pk=p.pk).update(**upd)          # the same field the admin switches on
    k.status = PersonKyc.APPROVED if act == "approve" else PersonKyc.REJECTED
    k.review_note, k.reviewed_by, k.reviewed_at = note, request.user, timezone.now()
    k.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
    try:
        from notifications.views import notify
        notify(k.user, "kyc", "\u2714 You now have the blue tick on XpertConnect." if act == "approve" else "Blue tick not approved: %s" % note, "/get-verified")
    except Exception:
        pass
    return Response(_out(k))
