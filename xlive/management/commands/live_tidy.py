from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "End lives whose host has gone (no beat for 75 s)"

    def handle(self, *a, **kw):
        from xlive.views import _tidy
        _tidy()
