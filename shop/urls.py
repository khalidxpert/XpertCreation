from django.urls import path

from . import views

urlpatterns = [path("", views.shop, name="shop"), path("orders/", views.order, name="shop-order"), path("orders/<int:pk>/simulate/", views.simulate, name="shop-simulate"),
               path("orders/<int:pk>/cancel/", views.cancel, name="shop-cancel"), path("orders/<int:pk>/refund/", views.refund, name="shop-refund"),
               path("admin/", views.admin, name="shop-admin")]
