from django.apps import AppConfig


class AutopostConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "autopost"
    verbose_name = "Official posts"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save

        def join_official_group(sender, instance, **kw):
            # every member joins the XpertCreation group once their email is verified (they can mute or leave)
            if getattr(instance, "is_email_verified", True) and instance.is_active:
                try:
                    from .posting import add_to_official_group
                    add_to_official_group(instance)
                except Exception:
                    pass

        post_save.connect(join_official_group, sender=get_user_model(), dispatch_uid="autopost_join_group")
