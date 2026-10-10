from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta), path("gigs/", views.gigs), path("gigs/<int:pk>/", views.gig),
    path("projects/", views.projects), path("projects/<int:pk>/", views.project), path("projects/<int:pk>/close/", views.project_close),
    path("projects/<int:pk>/bid/", views.bid), path("bids/<int:pk>/<str:act>/", views.bid_act),
    path("orders/", views.orders), path("orders/<int:pk>/", views.order), path("orders/<int:pk>/<str:act>/", views.order_act),
    path("pay/return/", views.pay_return), path("wallet/", views.wallet), path("wallet/withdraw/", views.withdraw),
    path("admin/", views.admin), path("admin/orders/<int:pk>/", views.admin_order), path("admin/payouts/<int:pk>/", views.admin_payout),
]
