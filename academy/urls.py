from django.urls import path

from . import views

app_name = "academy"

urlpatterns = [
    path('review/', views.course_review, name='course-review'),
    path('badges/', views.my_badges, name='my-badges'),
    path('board/medals/', views.badge_board, name='badge-board'),
    path('videos/', views.videos_list, name='videos-list'),
    path('videos/add/', views.videos_add, name='videos-add'),
    path('videos/mine/', views.videos_mine, name='videos-mine'),
    path('videos/queue/', views.videos_queue, name='videos-queue'),
    path('videos/<int:pk>/edit/', views.videos_edit, name='videos-edit'),
    path('videos/<int:pk>/delete/', views.videos_delete, name='videos-delete'),
    path('videos/<int:pk>/vote/', views.videos_vote, name='videos-vote'),
    path('videos/<int:pk>/seen/', views.videos_seen, name='videos-seen'),
    path('videos/<int:pk>/decide/', views.videos_decide, name='videos-decide'),
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
