"""Admin configuration for the attendance app."""

from django.contrib import admin

from .models import Attendance, Expense, Leave, MonthlyBudget, UserPreference


@admin.register(MonthlyBudget)
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "month", "amount", "updated_at")
    list_filter = ("user", "year", "month")
    ordering = ("-year", "-month")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "category", "amount", "note")
    list_filter = ("category", "user", "date")
    search_fields = ("note", "user__name")
    date_hierarchy = "date"
    ordering = ("-date",)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "show_wfh", "per_day_salary", "updated_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "status", "check_in", "check_out", "total_hours")
    list_filter = ("status", "user", "date")
    search_fields = ("remarks", "user__name")
    date_hierarchy = "date"
    ordering = ("-date",)
    readonly_fields = ("total_hours", "created_at")


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ("leave_type", "user", "start_date", "end_date", "total_days", "status")
    list_filter = ("leave_type", "status", "user")
    search_fields = ("reason", "user__name")
    date_hierarchy = "start_date"
    ordering = ("-start_date",)
