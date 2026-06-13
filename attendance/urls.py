"""URL routes for the attendance app."""

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "attendance"

urlpatterns = [
    # Onboarding / landing page
    path("welcome/", views.welcome, name="welcome"),
    path("logout/", views.logout_view, name="logout"),
    # Preferences (in-app page)
    path("preferences/", views.preferences, name="preferences"),
    path("preferences/budget/set/", views.set_monthly_budget, name="set_monthly_budget"),
    path(
        "preferences/budget/<int:pk>/delete/",
        views.monthly_budget_delete,
        name="monthly_budget_delete",
    ),
    # Budget tracker
    path("budget/", views.budget, name="budget"),
    path("budget/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Attendance records are managed via the Django admin; the in-app
    # pages were removed, so send old links to the dashboard.
    path("attendance/", RedirectView.as_view(pattern_name="attendance:dashboard")),
    # The Leave management pages were removed — send old links to the dashboard.
    path("leaves/", RedirectView.as_view(pattern_name="attendance:dashboard")),
    # Calendar
    path("calendar/", views.attendance_calendar, name="calendar"),
    path("calendar/mark/", views.mark_attendance, name="mark_attendance"),
    # CSV export (used by the attendance list)
    path("reports/export/", views.export_csv, name="export_csv"),
    # The Reports page was removed — send old links to the dashboard.
    path("reports/", RedirectView.as_view(pattern_name="attendance:dashboard")),
    # The Analytics page was removed — send old links to the dashboard.
    path("analytics/", RedirectView.as_view(pattern_name="attendance:dashboard")),
]
