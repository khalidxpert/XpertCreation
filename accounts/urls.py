from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("csrf/", views.csrf, name="csrf"),

    path("register/", views.register, name="register"),
    path("verify-email/", views.verify_email, name="verify-email"),
    path("resend-verify/", views.resend_verify, name="resend-verify"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("forgot-password/", views.forgot_password, name="forgot-password"),
    path("reset-password/", views.reset_password, name="reset-password"),

    path("me/", views.me, name="me"),
    path("change-password/", views.change_password, name="change-password"),
    path("delete-account/", views.delete_account, name="delete-account"),
    path("avatars/", views.avatars, name="avatars"),
    path("home/", views.home_card, name="home-card"),
    path("birthday/", views.set_birthday, name="set-birthday"),
    path("vibe/", views.set_vibe, name="set-vibe"),
    path("avatar/", views.set_avatar, name="set-avatar"),
    path("privacy/", views.set_privacy, name="set-privacy"),
]
