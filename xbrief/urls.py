from django.urls import path

from . import views

app_name = "xbrief"

urlpatterns = [
    path("", views.home, name="home"),
    path("folders/", views.folders, name="folders"),
    path("folders/<int:pk>/", views.folder, name="folder"),
    path("docs/", views.upload, name="upload"),
    path("docs/<int:pk>/", views.doc, name="doc"),
    path("docs/<int:pk>/file/", views.doc_file, name="doc_file"),
    path("docs/<int:pk>/share/", views.share, name="share"),
    path("s/<str:token>/", views.shared, name="shared"),
]
