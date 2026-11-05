from django.apps import AppConfig


class TgacademyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tgacademy"

    def ready(self):
        from . import hooks
        hooks.install()
