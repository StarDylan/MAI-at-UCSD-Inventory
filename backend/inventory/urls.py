from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("view_database/", views.view_database, name="view_database"),

]