from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Ad, AdImage, Category, Favorite, Report
from .serializers import AdDetailSerializer, AdListSerializer, CategorySerializer

MAX_IMAGES = 6


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.seller_id == getattr(request.user, "id", None)


class AdListCreate(generics.ListCreateAPIView):
    """Browse the board, or post a new ad when signed in."""

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        return AdListSerializer if self.request.method == "GET" else AdDetailSerializer

    def get_queryset(self):
        qs = (
            Ad.objects.filter(status="active")
            .select_related("category", "seller")
            .prefetch_related("images")
        )
        p = self.request.query_params

        q = (p.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if p.get("category"):
            qs = qs.filter(category__slug=p["category"])
        if p.get("city"):
            qs = qs.filter(city__iexact=p["city"])
        if p.get("condition") in ("new", "used"):
            qs = qs.filter(condition=p["condition"])
        if (p.get("min_price") or "").isdigit():
            qs = qs.filter(price__gte=int(p["min_price"]))
        if (p.get("max_price") or "").isdigit():
            qs = qs.filter(price__lte=int(p["max_price"]))

        sort = p.get("sort")
        if sort == "price_asc":
            qs = qs.order_by("price")
        elif sort == "price_desc":
            qs = qs.order_by("-price")
        else:
            qs = qs.order_by("-created_at")
        return qs

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "login"}, status=status.HTTP_401_UNAUTHORIZED)
        return super().create(request, *args, **kwargs)


class AdDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ad.objects.select_related("category", "seller").prefetch_related("images")
    serializer_class = AdDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        ad = self.get_object()
        Ad.objects.filter(pk=ad.pk).update(views=F("views") + 1)
        ad.refresh_from_db(fields=["views"])
        return Response(self.get_serializer(ad).data)


class MyAds(generics.ListAPIView):
    serializer_class = AdListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Ad.objects.filter(seller=self.request.user)
            .select_related("category", "seller")
            .prefetch_related("images")
        )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def category_list(request):
    qs = Category.objects.annotate(
        count=Count("ads", filter=Q(ads__status="active"))
    ).order_by("order", "name")
    return Response(CategorySerializer(qs, many=True, context={"request": request}).data)


@api_view(["POST"])
def favorite_toggle(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, ad=ad)
    if not created:
        fav.delete()
    return Response({"favorited": created})


@api_view(["GET"])
def favorites(request):
    qs = (
        Ad.objects.filter(favorites__user=request.user)
        .select_related("category", "seller")
        .prefetch_related("images")
    )
    return Response(AdListSerializer(qs, many=True, context={"request": request}).data)


@api_view(["POST"])
def report(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    reason = (request.data.get("reason") or "").strip()[:200]
    if not reason:
        return Response({"detail": "reason required"}, status=400)
    Report.objects.create(ad=ad, user=request.user, reason=reason)
    return Response({"ok": True})


@api_view(["POST"])
def upload_image(request, pk):
    ad = get_object_or_404(Ad, pk=pk, seller=request.user)
    if ad.images.count() >= MAX_IMAGES:
        return Response({"detail": "max %d photos" % MAX_IMAGES}, status=400)
    f = request.FILES.get("image")
    if not f:
        return Response({"detail": "image required"}, status=400)
    if f.size > 6 * 1024 * 1024:
        return Response({"detail": "file too large"}, status=400)
    img = AdImage.objects.create(ad=ad, image=f, order=ad.images.count())
    return Response(
        {"id": img.id, "url": request.build_absolute_uri(img.image.url)}, status=201
    )


@api_view(["POST"])
def mark_sold(request, pk):
    ad = get_object_or_404(Ad, pk=pk, seller=request.user)
    ad.status = "sold" if ad.status == "active" else "active"
    ad.save(update_fields=["status"])
    return Response({"status": ad.status})


@ensure_csrf_cookie
def csrf(request):
    """Plain Django view: only this layer's response passes through the CSRF
    middleware, so the cookie is actually written here."""
    return JsonResponse({"ok": True, "token": get_token(request)})
