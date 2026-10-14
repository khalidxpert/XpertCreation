from django.urls import path

from . import views

urlpatterns = [
    path("kit/", views.kit),
    path("work/<int:uid>/", views.work),
    path("shop/<slug:slug>/", views.shop),
    path("buttons/", views.buttons_save),
    path("buttons/<int:uid>/", views.buttons),
    path("buttons/<int:uid>/click/", views.button_click),
]
