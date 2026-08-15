from django.urls import path

from . import views

app_name = "academy"

urlpatterns = [
    path("courses/", views.courses, name="courses"),
    path("progress/", views.my_progress, name="my-progress"),
    path("progress/set/", views.set_progress, name="set-progress"),

    path("quiz/<slug:slug>/start/", views.start_quiz, name="quiz-start"),
    path("quiz/<slug:slug>/submit/", views.submit_quiz, name="quiz-submit"),

    path("certificates/", views.my_certificates, name="my-certificates"),
    path("learners/", views.learners, name="learners"),
    path("verify/<str:serial>/", views.verify, name="verify"),

    path("page/<str:serial>/", views.certificate_page, name="certificate-page"),
]
