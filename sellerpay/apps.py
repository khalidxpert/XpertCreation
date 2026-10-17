from django.apps import AppConfig


class SellerpayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sellerpay"
    verbose_name = "Pay the seller directly (JazzCash, EasyPaisa, bank)"
