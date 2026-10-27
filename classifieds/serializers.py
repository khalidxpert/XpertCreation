from rest_framework import serializers

from .models import Ad, AdImage, Category


class CategorySerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "count"]


class AdImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = AdImage
        fields = ["id", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class AdListSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    cover = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = [
            "id", "title", "price", "price_type", "condition",
            "city", "area", "category", "category_slug",
            "cover", "seller_name", "created_at",
        ]

    def get_cover(self, obj):
        first = obj.images.first()
        if not first:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(first.image.url) if request else first.image.url

    def get_seller_name(self, obj):
        return (obj.seller.full_name or "User")[:40]


class AdDetailSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    images = AdImageSerializer(many=True, read_only=True)
    seller_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = [
            "id", "title", "description", "price", "price_type", "condition",
            "city", "area", "phone", "status", "views", "created_at",
            "category", "category_slug", "category_id", "images",
            "seller_name", "is_mine",
        ]
        read_only_fields = ["views", "created_at", "status"]

    def get_seller_name(self, obj):
        return (obj.seller.full_name or "User")[:40]

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.seller_id == request.user.id)
