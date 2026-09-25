from django.apps import AppConfig


class AuditlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "auditlog"
    verbose_name = "System log"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save

        def joined(sender, instance, created, **kw):
            if created:
                from .models import AuditEvent
                AuditEvent.objects.create(user=instance, action="Joined (account created)", category="account")

        post_save.connect(joined, sender=get_user_model(), dispatch_uid="auditlog_joined")
