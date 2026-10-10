from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.meta),
    path("create/", views.create),
    path("join/", views.join),
    path("team/", views.team),
    path("f/<int:fid>/", views.family),
    path("f/<int:fid>/people/", views.add_person),
    path("f/<int:fid>/me/", views.this_is_me),
    path("f/<int:fid>/members/", views.requests_list),
    path("f/<int:fid>/members/<int:mid>/<str:act>/", views.member_act),
    path("f/<int:fid>/invite/", views.invite),
    path("f/<int:fid>/leave/", views.leave),
    path("f/<int:fid>/notices/", views.notices),
    path("f/<int:fid>/photos/", views.photos),
    path("f/<int:fid>/export/", views.export),
    path("p/<int:pid>/", views.person),
    path("p/<int:pid>/photo/", views.person_photo),
    path("notices/<int:nid>/", views.notice),
    path("photos/<int:phid>/", views.photo),
    path("invite/<str:token>/", views.invite_open),
]
