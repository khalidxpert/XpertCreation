from django.apps import AppConfig


class OwnerautoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ownerauto"
    verbose_name = "Owner auto-accept and welcome email"

    def ready(self):
        from . import signals  # noqa: F401
