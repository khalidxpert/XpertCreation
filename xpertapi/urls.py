from django.contrib import admin
from django.urls import include, path

from academy import views as academy_views

from django.conf import settings
from django.conf.urls.static import static

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
    path("api/mod/", include("moderation.urls")),
    path("api/vcard/", include("vcard.urls")),
    path("api/donate/", include("donations.urls")),
    path("api/notify/", include("notifications.urls")),
    path("api/botlink/", include("botlink.urls")),
    path("api/network/", include("network.urls")),
    path("api/pets/", include("pets.urls")),
    path("api/screen/", include("screen.urls")),

    path("api/auditlog/", include("auditlog.urls")),
    path("api/jobs/", include("jobs.urls")),
    path("api/feed/", include("feed.urls")),
    # Mounted at the root so the link people share stays short and readable.
    path("certificate/<str:serial>/", academy_views.certificate_page, name="certificate"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
