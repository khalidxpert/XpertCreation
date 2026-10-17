from django.urls import path

from . import views

urlpatterns = [
    path("avail/", views.avail), path("me/", views.me), path("me/qr/", views.me_qr), path("order/<str:kind>/<int:oid>/", views.order),
    path("proof/<int:pk>/<str:act>/", views.proof_act), path("file/<int:pk>/", views.file), path("qr/<int:uid>/", views.qr),
]
