from django.urls import path

from . import views

urlpatterns = [path("", views.shop, name="shop"), path("orders/", views.order, name="shop-order"), path("orders/<int:pk>/simulate/", views.simulate, name="shop-simulate"),
               path("orders/<int:pk>/cancel/", views.cancel, name="shop-cancel"), path("orders/<int:pk>/refund/", views.refund, name="shop-refund"),
               path("admin/", views.admin, name="shop-admin"),
               path("safepay/return/", views.safepay_return, name="shop-safepay-return")]
urlpatterns += [path("safepay/webhook/", views.safepay_webhook, name="shop-safepay-webhook")]

urlpatterns += [path("orders/<int:pk>/receipt/", views.receipt, name="shop-receipt"),
                path("orders/<int:pk>/receipt/email/", views.receipt_email, name="shop-receipt-email")]
