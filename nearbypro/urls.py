from django.urls import path
from . import views

urlpatterns = [path("pass/", views.nearby_pass), path("sig/<str:room>/", views.sig)]
