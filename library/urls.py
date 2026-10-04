from django.urls import path

from . import views

urlpatterns = [path("", views.books, name="library"), path("<int:pk>/", views.book, name="library-book")]
