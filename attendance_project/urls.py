"""Root URL configuration for attendance_project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # All app routes live at the site root.
    path("", include("attendance.urls")),
]
