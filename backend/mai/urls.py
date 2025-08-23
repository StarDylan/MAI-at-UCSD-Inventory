from django.urls import include, path
from django.contrib import admin

urlpatterns = [
    path("", include("inventory.urls")),
    path("admin/", admin.site.urls),
]
