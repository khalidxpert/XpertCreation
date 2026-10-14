from django.urls import path

from . import views

urlpatterns = [
    path("kit/", views.kit),
    path("work/<int:uid>/", views.work),
    path("shop/<slug:slug>/", views.shop),
]
