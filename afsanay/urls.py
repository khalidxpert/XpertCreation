from django.urls import path

from . import views

urlpatterns = [path("", views.afsanay, name="afsanay"), path("review/", views.review, name="afsanay-review"), path("<int:pk>/", views.afsana, name="afsana"), path("<int:pk>/qist/", views.add_qist, name="afsana-add"),
               path("<int:pk>/qist/<int:n>/", views.qist, name="afsana-qist"), path("<int:pk>/<str:what>/", views.act, name="afsana-act")]
