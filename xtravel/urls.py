from django.urls import path

from . import views

urlpatterns = [
    path("hotels/", views.hotels),
    path("hotels/<slug:slug>/", views.hotel),
    path("tours/", views.tours),
    path("tours/<slug:slug>/", views.tour),
    path("tours/<slug:slug>/book/", views.book_tour),
    path("book/", views.book_room),
    path("my/", views.my_trips),
    path("my/<int:pk>/cancel/", views.my_cancel),
    path("my/<int:pk>/review/", views.my_review),
    path("manage/", views.manage),
    path("manage/places/", views.prop_save),
    path("manage/places/<int:pk>/", views.prop_save),
    path("manage/places/<int:pk>/photo/", views.prop_photo),
    path("manage/places/<int:pk>/rooms/", views.room_save),
    path("manage/places/<int:pk>/rooms/<int:rid>/", views.room_save),
    path("manage/places/<int:pk>/rooms/<int:rid>/photo/", views.room_photo),
    path("manage/places/<int:pk>/calendar/", views.calendar),
    path("manage/places/<int:pk>/block/", views.block),
    path("manage/tours/", views.tour_save),
    path("manage/tours/<int:pk>/", views.tour_save),
    path("manage/tours/<int:pk>/photo/", views.tour_photo),
    path("manage/bookings/<int:pk>/", views.booking_action),
    path("review/", views.review_queue),
]
