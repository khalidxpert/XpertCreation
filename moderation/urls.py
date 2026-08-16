from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("apply/", views.apply, name="apply"),
    path("applications/", views.applications, name="applications"),
    path("applications/<int:pk>/", views.decide_application, name="decide"),
    path("team/", views.team, name="team"),
    path("role-settings/", views.role_settings, name="role-settings"),
    path("tickets/", views.tickets, name="tickets"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket-detail"),
]
