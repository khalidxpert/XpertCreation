from django.urls import path

from . import views

urlpatterns = [path("", views.search, name="bus"), path("manage/", views.manage, name="bus-manage"), path("<int:pk>/report/", views.report, name="bus-report")]
