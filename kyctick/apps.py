from django.apps import AppConfig


class KyctickConfig(AppConfig):
    """ID check (KYC) and the blue tick are two different things:
    - KYC approved = "ID verified": enough to open a shop, sell, list property, drive.
    - Blue tick = a PAID badge: it switches on only when the member has a paid Blue tick order AND an approved ID."""
    name = "kyctick"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.apps import apps
        from django.db.models.signals import post_save
        from .logic import on_kyc, on_order
        try:
            post_save.connect(on_order, sender=apps.get_model("shop", "Order"), dispatch_uid="kyctick_order")
            post_save.connect(on_kyc, sender=apps.get_model("companies", "PersonKyc"), dispatch_uid="kyctick_kyc")
        except LookupError:
            pass
