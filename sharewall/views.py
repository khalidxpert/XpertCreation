"""Post a result (quiz score, calculator result...) on the member's own XpertConnect wall."""
from datetime import timedelta

from django.apps import apps
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def wall(request):
    text = str(request.data.get("text") or "").strip()
    if len(text) < 3 or len(text) > 2000:
        return Response({"detail": "Write 3 to 2000 characters."}, status=400)
    Post = apps.get_model("feed", "Post")
    if Post.objects.filter(author=request.user, created_at__gte=timezone.now() - timedelta(minutes=10)).count() >= 5:
        return Response({"detail": "You have posted a lot just now. Please wait a few minutes."}, status=429)
    p = Post.objects.create(author=request.user, body=text, visibility="members")
    return Response({"ok": True, "id": p.id})
