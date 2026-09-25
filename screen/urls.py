from django.urls import path

from . import views

urlpatterns = [
    path("lists/<str:name>/", views.lists, name="screen-lists"),
    path("search/", views.search, name="screen-search"),
    path("title/<str:kind>/<int:tid>/", views.title, name="screen-title"),
    path("title/<str:kind>/<int:tid>/review/", views.review, name="screen-review"),
    path("title/<str:kind>/<int:tid>/list/", views.toggle_list, name="screen-list-toggle"),
    path("me/list/", views.my_list, name="screen-my-list"),
]
