from django.apps import AppConfig


class XcamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "xcam"
    verbose_name = "XpertCam clips in chat"

    def ready(self):
        from . import clips
        clips.patch()
