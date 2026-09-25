from django.urls import path

from . import views

app_name = "donations"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("categories/", views.categories, name="categories"),
    path("post/", views.post_item, name="post"),
    path("mine/", views.my_items, name="mine"),
    path("mine/requests/", views.my_requests, name="my-requests"),
    path("<int:pk>/withdraw/", views.withdraw_item, name="withdraw"),
    path("<int:pk>/ask/", views.ask, name="ask"),
    path("<int:pk>/requests/", views.item_requests, name="item-requests"),
    path("<int:pk>/report/", views.report, name="report"),
    path("requests/<int:pk>/decide/", views.decide, name="decide"),
    path("<int:pk>/given/", views.mark_given, name="given"),
]
