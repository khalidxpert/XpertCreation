from django.urls import path

from . import views

urlpatterns = [
    path("beat/", views.beat, name="rewards-beat"),
    path("board/", views.board, name="rewards-board"),
    path("me/", views.me, name="rewards-me"),
    path("state/", views.state, name="rewards-state"),
    path("spin/", views.spin, name="rewards-spin"),
    path("winners/", views.winners, name="rewards-winners"),
    path("wallet/", views.wallet, name="rewards-wallet"),
    path("step/", views.step, name="rewards-step"),
    path("withdraw/", views.withdraw, name="rewards-withdraw"),
    path("withdraw/<int:pk>/cancel/", views.withdraw_cancel, name="rewards-withdraw-cancel"),
    path("admin/withdrawals/", views.admin_list, name="rewards-admin-list"),
    path("admin/withdrawals/<int:pk>/", views.admin_act, name="rewards-admin-act"),
    path("proof/<int:pk>/", views.proof, name="rewards-proof"),
    path("card/<int:pk>/", views.card, name="rewards-card"),
]
