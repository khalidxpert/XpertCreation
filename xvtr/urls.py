from django.urls import path

from . import views

urlpatterns = [
    path("mine/", views.mine),
    path("new/", views.new),
    path("<int:pk>/", views.detail),
    path("<int:pk>/chunk/", views.chunk),
    path("<int:pk>/done/", views.done),
    path("<int:pk>/translate/", views.translate),
    path("<int:pk>/edit/", views.edit),
    path("<int:pk>/sub/", views.sub),
    path("<int:pk>/video/", views.video),
    path("<int:pk>/delete/", views.delete),
]
