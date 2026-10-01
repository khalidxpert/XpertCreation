from django.urls import path

from . import views

urlpatterns = [
    path("people/", views.people, name="feedx-people"),
    path("meta/", views.meta, name="feedx-meta"),
    path("feelings/", views.feelings, name="feedx-feelings"),
    path("posts/<int:pk>/meta/", views.set_meta, name="feedx-set-meta"),
]
