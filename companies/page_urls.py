from django.urls import re_path

from . import views

urlpatterns = [re_path(r"^company/(?P<slug>[a-z0-9-]{2,60})/?$", views.page)]
