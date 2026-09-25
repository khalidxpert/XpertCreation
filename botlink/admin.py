from django.contrib import admin

from .models import BotLink, LinkCode

admin.site.register(LinkCode)
admin.site.register(BotLink)
