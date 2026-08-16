from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("", views.all_summaries, name="all"),
    path("<str:module>/", views.module_reviews, name="module"),
    path("<str:module>/mine/", views.my_review, name="mine"),
]
