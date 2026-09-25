import io as _io
import logging
import os as _os

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (api_view, parser_classes,
                                       permission_classes, throttle_classes)
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import DonationItem, DonationPhoto, DonationRequest, DonationReport
from notifications.views import notify, notify_admins, open_thread


def _thread_for(req):
    """The chat id for an accepted request, or None.

    open_thread is get-or-create, so calling it here also backfills any
    request that was accepted before chat existed - without it those people
    would see an email address and no way to talk. It is only ever reached
    for requests already in the ACCEPTED state, so it cannot manufacture a
    conversation between two people who have no business having one.
    """
    if req.state != DonationRequest.ACCEPTED:
        return None
    return open_thread("donate", req.item_id, req.item.donor, req.requester).id

log = logging.getLogger(__name__)

MAX_PHOTOS = 3
MAX_UPLOAD = 12 * 1024 * 1024  # 12 MB - an iPhone HEIC is often over 4 MB, and
                               # we shrink it below anyway
MAX_SIDE = 1600                # nobody needs 12 megapixels of a used sofa


def normalise_photo(f):
    """Return the upload as an upright, reasonably sized JPEG.

    Two things were quietly breaking donations. iPhones upload HEIC, which
    Chrome and every Android browser refuse to render - the file saved fine
    and then showed as a blank box forever. And phones store the rotation in
    EXIF rather than in the pixels, so photos arrived on their side.

    If anything at all goes wrong we hand back the original untouched: a
    photo that might not display beats a post that will not save.
    """
    try:
        from PIL import Image, ImageOps
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except Exception:
            pass                      # not installed: other formats still work

        f.seek(0)
        im = Image.open(f)
        im = ImageOps.exif_transpose(im)      # honour the phone's rotation

        if im.mode not in ("RGB", "L"):
            # HEIC and PNG can carry transparency; JPEG cannot, so flatten
            # onto white rather than letting it turn black.
            bg = Image.new("RGB", im.size, (255, 255, 255))
            im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[3])
            im = bg
        elif im.mode == "L":
            im = im.convert("RGB")

        if max(im.size) > MAX_SIDE:
            ratio = MAX_SIDE / float(max(im.size))
            im = im.resize((max(1, int(im.size[0] * ratio)),
                            max(1, int(im.size[1] * ratio))), Image.LANCZOS)

        buf = _io.BytesIO()
        im.save(buf, "JPEG", quality=85, optimize=True)
        buf.seek(0)

        base = _os.path.splitext(_os.path.basename(getattr(f, "name", "photo")))[0]
        return InMemoryUploadedFile(buf, "ImageField", base + ".jpg",
                                    "image/jpeg", buf.getbuffer().nbytes, None)
    except Exception:
        log.exception("photo could not be normalised, storing as uploaded")
        try:
            f.seek(0)
        except Exception:
            pass
        return f


def _err(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


class PostThrottle(SimpleRateThrottle):
    scope = "donate_post"
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class RequestThrottle(SimpleRateThrottle):
    scope = "donate_request"
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def item_summary(it, request_user=None):
    out = {
        "id": it.id, "category": it.get_category_display(),
        "title": it.title, "description": it.description,
        "condition": it.get_condition_display(), "quantity": it.quantity,
        "city": it.city, "state": it.state,
        "photos": [p.image.url for p in it.photos.all()[:MAX_PHOTOS]],
        "donor_name": (it.donor.full_name or "").strip() or it.donor.email.split("@")[0],
        "created": it.created_at.strftime("%d %b %Y"),
        "mine": bool(request_user and request_user.id == it.donor_id),
    }
    if request_user and request_user.id == it.donor_id:
        out["request_count"] = it.requests.filter(state=DonationRequest.PENDING).count()
    return out


@api_view(["GET"])
@permission_classes([AllowAny])
def browse(request):
    """?category=books&city=Lahore"""
    qs = DonationItem.objects.filter(state=DonationItem.AVAILABLE).select_related("donor") \
                             .prefetch_related("photos")
    cat = request.GET.get("category")
    if cat and cat in dict(DonationItem.CATEGORIES):
        qs = qs.filter(category=cat)
    city = (request.GET.get("city") or "").strip()
    if city:
        qs = qs.filter(city__iexact=city)

    rows = list(qs[:80])
    # Anyone may browse, so there may be no user at all. Without passing one
    # through, "mine" was false for everybody and a donor was invited to ask
    # themselves for their own sofa.
    viewer = request.user if request.user.is_authenticated else None
    return Response({"items": [item_summary(it, viewer) for it in rows],
                     "count": len(rows)})


@api_view(["GET"])
@permission_classes([AllowAny])
def categories(request):
    counts = {c: 0 for c, _ in DonationItem.CATEGORIES}
    for row in (DonationItem.objects.filter(state=DonationItem.AVAILABLE)
               .values_list("category", flat=True)):
        counts[row] = counts.get(row, 0) + 1
    return Response({"categories": [
        {"key": k, "name": n, "count": counts.get(k, 0)} for k, n in DonationItem.CATEGORIES
    ]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PostThrottle])
@parser_classes([MultiPartParser])
def post_item(request):
    """multipart: title, category, condition, quantity, city, description,
    photo0, photo1, photo2"""
    title = str(request.data.get("title") or "").strip()[:120]
    category = request.data.get("category")
    condition = request.data.get("condition", "good")
    city = str(request.data.get("city") or "").strip()[:60]
    description = str(request.data.get("description") or "").strip()[:1000]
    try:
        quantity = max(1, min(50, int(request.data.get("quantity") or 1)))
    except (TypeError, ValueError):
        quantity = 1

    if len(title) < 3:
        return _err("Give it a short title.")
    if category not in dict(DonationItem.CATEGORIES):
        return _err("Pick a category.")
    if condition not in dict(DonationItem.CONDITIONS):
        condition = "good"
    if not city:
        return _err("Which city is this in?")

    photos = [request.FILES.get("photo0"), request.FILES.get("photo1"),
             request.FILES.get("photo2")]
    photos = [p for p in photos if p]
    for p in photos:
        if p.size > MAX_UPLOAD:
            return _err("Each photo needs to be under 12 MB.")
        ctype = (p.content_type or "").lower()
        name = (getattr(p, "name", "") or "").lower()
        # Some Android builds send HEIC with an empty or octet-stream type,
        # so the filename has to count as evidence too.
        looks_like_image = (ctype.startswith("image/")
                            or name.endswith((".heic", ".heif", ".jpg", ".jpeg",
                                              ".png", ".webp", ".gif")))
        if not looks_like_image:
            return _err("Only image files are accepted.")

    item = DonationItem.objects.create(
        donor=request.user, category=category, title=title,
        description=description, condition=condition, quantity=quantity, city=city)
    for p in photos[:MAX_PHOTOS]:
        DonationPhoto.objects.create(item=item, image=normalise_photo(p))

    who = (request.user.full_name or "").strip() or request.user.email.split("@")[0]
    notify_admins("donate_new_post", who + " posted \"" + title + "\" (" + category + ").",
                 "/donate")

    return Response({"id": item.id, "detail": "Posted."}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_items(request):
    rows = (DonationItem.objects.filter(donor=request.user)
            .exclude(state=DonationItem.REMOVED)
            .prefetch_related("photos", "requests"))
    return Response({"items": [item_summary(it, request.user) for it in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw_item(request, pk):
    """Donor removes their own listing."""
    it = DonationItem.objects.filter(id=pk, donor=request.user).first()
    if not it:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    it.state = DonationItem.REMOVED
    it.save(update_fields=["state", "updated_at"])
    return Response({"detail": "Removed."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([RequestThrottle])
def ask(request, pk):
    """A needy person asks for an item."""
    it = DonationItem.objects.filter(id=pk, state=DonationItem.AVAILABLE).first()
    if not it:
        return _err("This is no longer available.", status.HTTP_404_NOT_FOUND)
    if it.donor_id == request.user.id:
        return _err("This is your own listing.")

    existing = DonationRequest.objects.filter(item=it, requester=request.user).first()
    if existing and existing.state == DonationRequest.PENDING:
        return _err("You already asked for this.")

    message = str(request.data.get("message") or "").strip()[:300]
    if existing:
        existing.state = DonationRequest.PENDING
        existing.message = message
        existing.decided_at = None
        existing.save()
    else:
        DonationRequest.objects.create(item=it, requester=request.user, message=message)

    who = (request.user.full_name or "").strip() or request.user.email.split("@")[0]
    notify(it.donor, "donate_request", who + ' asked for "' + it.title + '".', "/donate")

    return Response({"detail": "Sent. The donor will see your request."},
                    status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def item_requests(request, pk):
    """Donor sees who has asked. No contact details yet - only after accept."""
    it = DonationItem.objects.filter(id=pk, donor=request.user).first()
    if not it:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)

    rows = it.requests.exclude(state=DonationRequest.WITHDRAWN) \
                      .select_related("requester", "item", "item__donor")
    return Response({"requests": [{
        "id": r.id,
        "name": (r.requester.full_name or "").strip() or r.requester.email.split("@")[0],
        "message": r.message, "state": r.state,
        "contact": r.requester.email if r.state == DonationRequest.ACCEPTED else None,
        "thread": _thread_for(r),
        "when": r.created_at.strftime("%d %b"),
    } for r in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decide(request, pk):
    """Donor accepts or declines one request. body: {accept: true|false}"""
    r = DonationRequest.objects.filter(id=pk, item__donor=request.user) \
                               .select_related("item", "requester").first()
    if not r:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    if r.state != DonationRequest.PENDING:
        return _err("Already decided.")

    accept = bool(request.data.get("accept"))
    r.state = DonationRequest.ACCEPTED if accept else DonationRequest.DECLINED
    r.decided_at = timezone.now()
    r.save()

    thread_id = None
    if accept:
        r.item.state = DonationItem.RESERVED
        r.item.save(update_fields=["state", "updated_at"])

        notify(r.requester, "donate_accepted",
              (r.item.donor.full_name or r.item.donor.email.split("@")[0])
              + ' accepted your request for "' + r.item.title + '".', "/donate")

        t = open_thread("donate", r.item.id, r.item.donor, r.requester)
        thread_id = t.id

    return Response({"detail": "Accepted." if accept else "Declined.",
                     "contact": r.requester.email if accept else None,
                     "thread": thread_id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_given(request, pk):
    it = DonationItem.objects.filter(id=pk, donor=request.user).first()
    if not it:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    it.state = DonationItem.GIVEN
    it.given_at = timezone.now()
    it.save(update_fields=["state", "given_at", "updated_at"])
    return Response({"detail": "Marked as given. Thank you."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_requests(request):
    rows = (DonationRequest.objects.filter(requester=request.user)
            .exclude(state=DonationRequest.WITHDRAWN)
            .select_related("item", "item__donor", "requester")
            .prefetch_related("item__photos"))
    return Response({"requests": [{
        "id": r.id, "state": r.state,
        "item": item_summary(r.item, request.user),
        "contact": r.item.donor.email if r.state == DonationRequest.ACCEPTED else None,
        "thread": _thread_for(r),
    } for r in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report(request, pk):
    it = DonationItem.objects.filter(id=pk).first()
    if not it:
        return _err("Not found.", status.HTTP_404_NOT_FOUND)
    reason = str(request.data.get("reason") or "").strip()[:300]
    if len(reason) < 5:
        return _err("Say a little about what is wrong.")
    DonationReport.objects.create(item=it, reporter=request.user, reason=reason)
    return Response({"detail": "Reported. Thank you for flagging it."})
