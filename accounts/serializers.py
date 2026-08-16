import re

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User

PHONE_RE = re.compile(r"^\+\d{8,15}$")


def _validate_password(value):
    try:
        password_validation.validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))
    return value


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # Optional at sign-up. Day and month are enough for a birthday; the year
    # is an age, which is not needed to open an account.
    birth_day = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    birth_month = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=12)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    preferred_lang = serializers.CharField(max_length=5, required=False, default="en")

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        value = (value or "").strip().replace(" ", "").replace("-", "")
        if value and not PHONE_RE.match(value):
            raise serializers.ValidationError(
                "Use international format, for example +923001234567."
            )
        return value

    def validate_password(self, value):
        return _validate_password(value)

    def validate(self, data):
        local = data["email"].split("@")[0]
        if len(local) > 3 and local.lower() in data["password"].lower():
            raise serializers.ValidationError(
                {"password": "Password must not contain your email address."}
            )
        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


class EmailOnlySerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class CodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$")

    def validate_email(self, value):
        return value.lower().strip()


class ResetConfirmSerializer(CodeSerializer):
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    def validate_new_password(self, value):
        return _validate_password(value)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    def validate_new_password(self, value):
        return _validate_password(value)


class MeSerializer(serializers.ModelSerializer):
    can_order = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "phone", "is_email_verified",
            "can_order", "daily_limit_pkr", "preferred_lang", "date_joined",
            "hide_from_leaderboard", "avatar",
            "birth_day", "birth_month", "birth_year", "show_birthday",
            "vibe",
        ]
        read_only_fields = [
            "id", "email", "is_email_verified", "can_order",
            "daily_limit_pkr", "date_joined",
        ]
