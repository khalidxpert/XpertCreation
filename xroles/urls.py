from django.urls import path
from . import views

urlpatterns = [
    path("<int:gid>/roles/", views.roles),
    path("<int:gid>/roles/order/", views.order),
    path("<int:gid>/roles/<int:rid>/", views.role),
    path("<int:gid>/roles/<int:rid>/members/", views.give),
]
