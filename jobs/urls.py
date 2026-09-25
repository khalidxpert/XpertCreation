from django.urls import path

from . import views

urlpatterns = [
    path("", views.jobs, name="jobs"),
    path("mine/", views.my_jobs, name="jobs-mine"),
    path("applied/", views.my_applications, name="jobs-applied"),
    path("for-me/", views.for_me, name="jobs-for-me"),
    path("<int:pk>/", views.job_detail, name="job"),
    path("<int:pk>/apply/", views.apply, name="job-apply"),
    path("<int:pk>/withdraw/", views.withdraw, name="job-withdraw"),
    path("<int:pk>/applicants/", views.applicants, name="job-applicants"),
    path("<int:pk>/report/", views.report, name="job-report"),
    path("applications/<int:pk>/status/", views.set_status, name="application-status"),
]
