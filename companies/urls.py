from django.urls import path

from . import person, views

urlpatterns = [
    path("mine/", views.mine, name="co-mine"),
    path("kyc/me/", person.me, name="kyc-me"),
    path("kyc/me/docs/", person.docs, name="kyc-me-docs"),
    path("kyc/me/submit/", person.submit, name="kyc-me-submit"),
    path("kyc/docs/<int:doc>/", person.doc_file, name="kyc-doc"),
    path("kyc/review/", person.review_list, name="kyc-review-list"),
    path("kyc/<int:pk>/review/", person.review, name="kyc-review"),
    path("search/", views.search, name="co-search"),
    path("review/", views.review_list, name="co-review-list"),
    path("docs/<int:doc>/", views.doc_file, name="co-doc"),
    path("public/<slug:slug>/", views.public, name="co-public"),
    path("public/<slug:slug>/posts/", views.posts, name="co-posts"),
    path("<int:pk>/", views.company, name="co-company"),
    path("<int:pk>/image/", views.image, name="co-image"),
    path("<int:pk>/domain/", views.domain, name="co-domain"),
    path("<int:pk>/docs/", views.docs, name="co-docs"),
    path("<int:pk>/submit/", views.submit, name="co-submit"),
    path("<int:pk>/review/", views.review, name="co-review"),
]
