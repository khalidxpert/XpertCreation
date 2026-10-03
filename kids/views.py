"""Kids page: videos from staff-chosen official YouTube channels only. No comments, no sign-in, no data collected."""
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .fetch import latest, resolve
from .models import KidsChannel, KidsVideo


def _staff(u):
    return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


def refresh(ch, keep=30):
    rows = latest(ch.channel_id)[:keep]
    for vid, title, when in rows:
        KidsVideo.objects.update_or_create(video_id=vid, defaults={"channel": ch, "title": title, "published": when})
    old = KidsVideo.objects.filter(channel=ch).order_by("-published").values_list("id", flat=True)[60:]
    KidsVideo.objects.filter(id__in=list(old)).delete()
    ch.fetched_at = timezone.now(); ch.save(update_fields=["fetched_at"])
    return len(rows)


@api_view(["GET"])
@permission_classes([AllowAny])
def videos(request):
    qs = KidsVideo.objects.filter(hidden=False, channel__active=True).select_related("channel")
    cat, age = request.GET.get("cat"), request.GET.get("age")
    if cat in dict(KidsChannel.CATS): qs = qs.filter(channel__category=cat)
    if age in ("2-5", "6-10"): qs = qs.filter(channel__age__in=[age, "all"])
    out = {"videos": [{"id": v.video_id, "title": v.title, "channel": v.channel.name, "cat": v.channel.category} for v in qs.order_by("-published")[:120]],
           "cats": [{"key": k, "name": n} for k, n in KidsChannel.CATS], "staff": _staff(request.user)}
    if out["staff"]:
        out["channels"] = [{"id": c.id, "name": c.name, "cat": c.category, "age": c.age, "active": c.active, "videos": c.videos.count()} for c in KidsChannel.objects.order_by("name")]
    return Response(out)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def channels(request, pk=None):
    if not _staff(request.user):
        return Response({"detail": "Staff only."}, status=403)
    if request.method == "DELETE":
        KidsChannel.objects.filter(pk=pk).delete(); return Response({"deleted": True})
    d = request.data
    try:
        cid, name = resolve(str(d.get("url") or ""))
    except Exception:
        return Response({"detail": "Could not open that YouTube link. Check it and try again."}, status=400)
    if not cid:
        return Response({"detail": "That does not look like a YouTube channel link."}, status=400)
    ch, made = KidsChannel.objects.get_or_create(channel_id=cid, defaults={"name": name or cid})
    ch.category = d.get("cat") if d.get("cat") in dict(KidsChannel.CATS) else ch.category
    ch.age = d.get("age") if d.get("age") in dict(KidsChannel.AGES) else ch.age
    if name: ch.name = name
    ch.active = True; ch.save()
    try:
        n = refresh(ch)
    except Exception:
        n = 0
    return Response({"channel": ch.name, "new": made, "videos": n}, status=201 if made else 200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def hide(request, vid):
    if not _staff(request.user):
        return Response({"detail": "Staff only."}, status=403)
    KidsVideo.objects.filter(video_id=vid).update(hidden=True)
    return Response({"hidden": True})
