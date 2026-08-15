from django.urls import path

from . import views

app_name = "reminders"

urlpatterns = [
    path("birthdays/", views.birthdays, name="birthdays"),
    path("birthdays/<int:pk>/", views.birthday, name="birthday"),
]
