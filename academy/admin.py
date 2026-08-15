from django.contrib import admin

from .models import (
    Answer, Attempt, Certificate, Choice, Course, Lesson, LessonProgress, Question,
)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ["order", "key", "title", "minutes"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "order", "is_active",
                    "quiz_questions", "pass_percent", "min_lessons_percent"]
    list_editable = ["order", "is_active", "pass_percent"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LessonInline]


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ["order", "text", "is_correct"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["short", "course", "order", "is_active", "answer_count"]
    list_filter = ["course", "is_active"]
    search_fields = ["text"]
    inlines = [ChoiceInline]

    @admin.display(description="Question")
    def short(self, obj):
        return obj.text[:70]

    @admin.display(description="Correct answers")
    def answer_count(self, obj):
        """A question with zero or two correct answers is unanswerable.
        Surfacing the count makes that visible before a learner hits it."""
        return obj.choices.filter(is_correct=True).count()


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "score", "total", "percent", "passed", "started_at"]
    list_filter = ["course", "passed"]
    search_fields = ["user__email"]
    readonly_fields = [f.name for f in Attempt._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ["serial", "holder_name", "course_title",
                    "score_percent", "issued_at", "revoked"]
    list_filter = ["course", "revoked"]
    search_fields = ["serial", "holder_name", "user__email"]
    readonly_fields = ["serial", "holder_name", "course_title",
                       "score_percent", "issued_at", "attempt", "user", "course"]

    def has_add_permission(self, request):
        # Certificates are earned, never hand-created. If staff could mint one,
        # every certificate would be worthless.
        return False


admin.site.register(LessonProgress)
admin.site.register(Answer)
