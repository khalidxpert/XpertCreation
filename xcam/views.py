"""/api/cam/clip/<t|g>/<message id>/ - play a clip sent in a chat (t) or group (g), with seeking (Range)."""
import os
import re

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .clips import VIDEO_EXT


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def clip(request, kind, pk):
    from notifications import chatx
    from notifications.models import ChatMessage, GroupMember, GroupMessage
    u = request.user
    if kind == "t":
        m = ChatMessage.objects.select_related("thread").filter(pk=pk).exclude(attachment="").first()
        ok = bool(m and m.thread.has(u))
    elif kind == "g":
        m = GroupMessage.objects.filter(pk=pk, hidden=False).exclude(attachment="").first()
        ok = bool(m and GroupMember.objects.filter(group_id=m.group_id, user=u).exists())
    else:
        m, ok = None, False
    if not ok:
        return HttpResponse("Not found.", status=404)
    rel = str(m.attachment)
    ext = rel.rsplit(".", 1)[-1].lower()
    if ext not in VIDEO_EXT or ".." in rel:
        return HttpResponse("Not a clip.", status=404)
    path = os.path.join(chatx.FILES_DIR, rel)
    if not os.path.isfile(path):
        return HttpResponse("Not found.", status=404)
    size = os.path.getsize(path)
    start, end, status = 0, size - 1, 200
    rg = re.match(r"bytes=(\d*)-(\d*)$", request.META.get("HTTP_RANGE", ""))
    if rg and (rg.group(1) or rg.group(2)):
        if rg.group(1):
            start = int(rg.group(1)); end = int(rg.group(2)) if rg.group(2) else size - 1
        else:
            start = max(0, size - int(rg.group(2)))
        end = min(end, size - 1)
        if start > end:
            r = HttpResponse(status=416); r["Content-Range"] = "bytes */%d" % size; return r
        status = 206
    with open(path, "rb") as fh:
        fh.seek(start)
        data = fh.read(end - start + 1)
    r = HttpResponse(data, status=status, content_type=VIDEO_EXT[ext])
    r["Accept-Ranges"] = "bytes"
    r["Content-Length"] = str(len(data))
    if status == 206:
        r["Content-Range"] = "bytes %d-%d/%d" % (start, end, size)
    r["Cache-Control"] = "private, max-age=86400"
    r["X-Content-Type-Options"] = "nosniff"
    return r
