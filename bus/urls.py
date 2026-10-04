from django.urls import path

from . import views

urlpatterns = [path("", views.search, name="bus"), path("terminals/", views.terminals, name="bus-terminals"), path("manage/", views.manage, name="bus-manage"), path("<int:pk>/report/", views.report, name="bus-report")]
