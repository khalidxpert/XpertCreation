from django.urls import path
from . import views

urlpatterns = [
    path("qa/", views.qa, name="learnx-qa"),
    path("qa/counts/", views.qa_counts, name="learnx-qa-counts"),
    path("qa/<int:pk>/delete/", views.qa_delete, name="learnx-qa-delete"),
    path("qa/<int:pk>/helpful/", views.qa_helpful, name="learnx-qa-helpful"),
]
