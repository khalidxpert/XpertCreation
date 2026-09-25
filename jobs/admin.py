from django.contrib import admin

from .models import Application, Job, JobReport


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company", "poster", "city", "kind", "applicants_count", "deadline", "closed", "hidden")
    list_filter = ("hidden", "closed", "kind", "workplace")
    list_editable = ("hidden",)
    search_fields = ("title", "company", "description")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "applicant", "status", "created_at")
    list_filter = ("status",)


@admin.register(JobReport)
class JobReportAdmin(admin.ModelAdmin):
    list_display = ("job", "reporter", "reason", "handled", "created_at")
    list_filter = ("handled", "reason")
    list_editable = ("handled",)
