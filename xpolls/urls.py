from django.urls import path
from . import views

urlpatterns = [
    path("", views.create),
    path("<int:pk>/", views.detail),
    path("<int:pk>/vote/", views.vote),
    path("<int:pk>/close/", views.close),
]
