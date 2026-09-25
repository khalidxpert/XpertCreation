from django.urls import path

from . import views

urlpatterns = [
    path("mine/", views.mine, name="pets-mine"),
    path("upcoming/", views.upcoming, name="pets-upcoming"),
    path("templates/<str:species>/", views.templates, name="pets-templates"),
    path("<int:pk>/", views.pet_detail, name="pets-detail"),
    path("<int:pk>/delete/", views.pet_delete, name="pets-delete"),
    path("<int:pk>/photo/", views.pet_photo, name="pets-photo"),
    path("<int:pk>/lost/", views.pet_lost, name="pets-lost"),
    path("<int:pk>/schedule/", views.pet_schedule, name="pets-schedule"),
    path("<int:pk>/records/", views.record_save, name="pets-record-save"),
    path("records/<int:rid>/done/", views.record_done, name="pets-record-done"),
    path("records/<int:rid>/delete/", views.record_delete, name="pets-record-delete"),
    path("tag/<str:code>/", views.tag, name="pets-tag"),
    path("tag/<str:code>/found/", views.tag_found, name="pets-tag-found"),
    path("lost/", views.lost_board, name="pets-lost-board"),
    path("lost/<int:rid>/photo/", views.lost_photo, name="pets-lost-photo"),
    path("lost/<int:rid>/resolve/", views.lost_resolve, name="pets-lost-resolve"),
]
