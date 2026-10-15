from django.apps import AppConfig


class DatakeepConfig(AppConfig):
    name = "datakeep"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import pre_delete
        from .cleanup import on_user_delete
        pre_delete.connect(on_user_delete, sender=get_user_model(), dispatch_uid="datakeep_user_delete")
