from django.apps import AppConfig


class FeedxConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "feedx"
    verbose_name = "Connect extras"

    def ready(self):
        from django.db.models.signals import post_save
        from feed.models import Comment, Post
        from . import mentions
        post_save.connect(mentions.on_post, sender=Post, dispatch_uid="feedx_post_mentions")
        post_save.connect(mentions.on_comment, sender=Comment, dispatch_uid="feedx_comment_mentions")
