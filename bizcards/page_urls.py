from django.urls import re_path

from . import views

# served straight under the site (nginx sends these paths to Django)
urlpatterns = [
    re_path(r"^c/(?P<slug>[a-z0-9-]{5,40})/?$", views.page),
    re_path(r"^c/(?P<slug>[a-z0-9-]{5,40})\.vcf$", views.vcf),
    re_path(r"^card/(?P<token>[a-zA-Z0-9]+)/?$", views.legacy),
]
