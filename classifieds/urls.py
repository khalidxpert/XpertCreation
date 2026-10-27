from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.csrf, name="classifieds-csrf"),
    path("categories/", views.category_list, name="classifieds-categories"),
    path("ads/", views.AdListCreate.as_view(), name="classifieds-ads"),
    path("ads/<int:pk>/", views.AdDetail.as_view(), name="classifieds-ad"),
    path("ads/<int:pk>/favorite/", views.favorite_toggle, name="classifieds-favorite"),
    path("ads/<int:pk>/report/", views.report, name="classifieds-report"),
    path("ads/<int:pk>/images/", views.upload_image, name="classifieds-images"),
    path("ads/<int:pk>/sold/", views.mark_sold, name="classifieds-sold"),
    path("my/", views.MyAds.as_view(), name="classifieds-my"),
    path("favorites/", views.favorites, name="classifieds-favorites"),
]
