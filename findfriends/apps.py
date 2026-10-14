from django.apps import AppConfig


class FindfriendsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "findfriends"
    verbose_name = "Find people you know"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save
        from .views import on_user_saved
        post_save.connect(on_user_saved, sender=get_user_model(), dispatch_uid="findfriends_contact_joined")
