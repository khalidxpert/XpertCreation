from django.apps import AppConfig


class XbriefConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "xbrief"
    verbose_name = "My Briefcase"

    def ready(self):
        from django.db.models.signals import post_delete
        from .models import Doc
        from .store import remove

        def _gone(sender, instance, **kw):
            remove(instance.path)
        post_delete.connect(_gone, sender=Doc, dispatch_uid="xbrief_doc_gone")
