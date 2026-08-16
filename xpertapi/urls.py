from django.contrib import admin
from django.urls import include, path

from academy import views as academy_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/academy/", include("academy.urls")),
    path("api/typing/", include("typingtutor.urls")),
    path("api/blood/", include("bloodbank.urls")),
    path("api/reminders/", include("reminders.urls")),
    path("api/weather/", include("weather.urls")),
    path("api/games/", include("games.urls")),
    path("api/news/", include("news.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/where/", include("geo.urls")),

    # Mounted at the root so the link people share stays short and readable.
    path("certificate/<str:serial>/", academy_views.certificate_page, name="certificate"),
]
