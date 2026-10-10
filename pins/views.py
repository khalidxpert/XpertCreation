import re

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Pin

MAX = 3


def _clean(items):
    out, seen = [], set()
    for x in items if isinstance(items, list) else []:
        if not isinstance(x, dict):
            continue
        p = str(x.get("path") or "")[:200]
        if not re.match(r"^/[A-Za-z0-9/_\-.#=?&%]*$", p) or p in seen:
            continue
        seen.add(p)
        out.append({"path": p, "label": re.sub(r"\s+", " ", str(x.get("label") or p)).strip()[:40]})
        if len(out) >= MAX:
            break
    return out


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def pins(request):
    p, _ = Pin.objects.get_or_create(user=request.user)
    if request.method == "POST":
        p.items = _clean(request.data.get("items"))
        p.save()
    return Response({"items": p.items, "max": MAX})
