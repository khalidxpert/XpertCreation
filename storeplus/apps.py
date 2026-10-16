from django.apps import AppConfig


class StoreplusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "storeplus"
    verbose_name = "Store: countries, dropshipping, shop card"

    def ready(self):
        from . import patch
        patch.install()
