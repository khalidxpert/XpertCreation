from django.urls import path

from . import views

urlpatterns = [path("islamic/", views.islamic, name="corner-islamic"), path("poetry/", views.poetry, name="corner-poetry"),
               path("recipes/", views.recipes, name="corner-recipes"), path("recipes/<int:pk>/", views.recipe, name="corner-recipe")]
