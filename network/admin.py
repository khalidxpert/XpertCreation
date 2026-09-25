from django.contrib import admin
from django.utils import timezone

from notifications.views import notify

from .models import (Connection, Education, Endorsement, Experience, Follow, ProfileReport,
                     ProProfile, Skill, VerificationRequest)


@admin.register(ProProfile)
class ProProfileAdmin(admin.ModelAdmin):
    list_display = ("slug", "user", "visibility", "open_to_work", "verified", "updated_at")
    list_filter = ("visibility", "open_to_work", "verified")
    search_fields = ("slug", "user__email", "user__full_name", "headline")


@admin.register(ProfileReport)
class ProfileReportAdmin(admin.ModelAdmin):
    list_display = ("profile", "reporter", "reason", "handled", "created_at")
    list_filter = ("handled", "reason")


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "state", "created_at", "responded_at")
    list_filter = ("state",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")


@admin.action(description="Approve - give the blue tick")
def approve(modeladmin, request, queryset):
    now = timezone.now()
    for r in queryset.filter(state=VerificationRequest.PENDING).select_related("profile", "profile__user"):
        r.state, r.decided_at, r.decided_by = VerificationRequest.APPROVED, now, request.user
        r.save(update_fields=["state", "decided_at", "decided_by"])
        p = r.profile
        p.verified, p.verified_at = True, now
        p.save(update_fields=["verified", "verified_at"])
        notify(p.user, "tick", "Your blue tick has been approved.", "/in/%s" % p.slug)


@admin.action(description="Reject")
def reject(modeladmin, request, queryset):
    now = timezone.now()
    for r in queryset.filter(state=VerificationRequest.PENDING).select_related("profile", "profile__user"):
        r.state, r.decided_at, r.decided_by = VerificationRequest.REJECTED, now, request.user
        r.save(update_fields=["state", "decided_at", "decided_by"])
        notify(r.profile.user, "tick", "Your blue tick request was not approved this time.",
               "/in/%s" % r.profile.slug)


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("profile", "state", "followers_at_request", "created_at", "decided_by")
    list_filter = ("state",)
    actions = [approve, reject]


admin.site.register(Skill)
admin.site.register(Endorsement)
admin.site.register(Experience)
admin.site.register(Education)
