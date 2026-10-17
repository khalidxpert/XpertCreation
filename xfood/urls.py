from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta), path("list/", views.browse), path("r/<slug:slug>/", views.restaurant),
    path("orders/", views.orders), path("orders/<int:pk>/", views.order), path("orders/<int:pk>/<str:act>/", views.order_act),
    path("mine/", views.mine), path("mine/image/", views.mine_image), path("mine/menu/", views.menu), path("mine/item/", views.item_save),
    path("mine/item/<int:pk>/", views.item_one), path("mine/orders/", views.mine_orders), path("team/", views.team), path("team/<int:pk>/<str:act>/", views.team_act),
]
