from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta), path("home/", views.home), path("showcase/", views.showcase), path("products/", views.products), path("products/<int:pk>/", views.product),
    path("products/<int:pk>/image/", views.product_image), path("shops/<slug:slug>/", views.shop_page),
    path("merchant/", views.merchant_me), path("merchant/logo/", views.merchant_logo),
    path("orders/", views.orders), path("orders/<int:pk>/", views.order), path("orders/<int:pk>/<str:act>/", views.order_act),
    path("seller/orders/", views.seller_orders), path("inventory/", views.inventory), path("inventory/<int:pk>/", views.stock_moves), path("quotes/", views.quotes), path("quotes/<int:pk>/reply/", views.quote_reply),
    path("pay/return/", views.pay_return), path("reviews/<int:pk>/reply/", views.review_reply), path("team/", views.team), path("team/<str:kind>/<int:pk>/", views.team_act),
]
