from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .checks import blockers


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check(request):
    """Can I delete my account now? Lists what to finish first."""
    b = blockers(request.user)
    return Response({"can_delete": not b, "first": b})
