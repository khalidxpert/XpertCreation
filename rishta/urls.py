from django.urls import path
from . import views

urlpatterns = [
    path("config/", views.config),
    path("me/", views.me),
    path("me/photo/", views.photo_upload),
    path("photo/<int:pid>/", views.photo),
    path("browse/", views.browse),
    path("p/<int:pid>/", views.detail),
    path("p/<int:pid>/interest/", views.send_interest),
    path("p/<int:pid>/block/", views.block),
    path("p/<int:pid>/report/", views.report),
    path("p/<int:pid>/moderate/", views.moderate),
    path("interests/", views.interests),
    path("interests/<int:iid>/answer/", views.answer),
    path("interests/<int:iid>/withdraw/", views.withdraw),
    path("cases/", views.cases),
    path("cases/<int:cid>/", views.case_update),
]
