from django.urls import path

from . import views

urlpatterns = [
    path("mine/", views.mine),
    path("<int:pk>/", views.remove),
    path("register/options/", views.reg_options),
    path("register/verify/", views.reg_verify),
    path("login/options/", views.login_options),
    path("login/verify/", views.login_verify),
]
