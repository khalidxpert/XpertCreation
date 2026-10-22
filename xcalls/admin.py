from django.contrib import admin
from .models import Call, CallMember


class MemberInline(admin.TabularInline):
    model = CallMember
    extra = 0


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "ref_id", "caller", "video", "state", "created", "answered_at", "ended_at")
    list_filter = ("state", "video", "kind")
    inlines = [MemberInline]
