"""
Database models for the personal attendance management system.

Models:
    * UserPreference  — a named profile (name + WFH preference + salary).
    * Attendance      — one row per calendar day, owned by a user.
    * Leave           — applied leaves with a date range, owned by a user.

Per-month statistics are computed on the fly (see views), scoped per user.
"""

from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone


class UserPreference(models.Model):
    """
    Single-user onboarding/preferences captured on the landing page.

    ``show_wfh`` controls whether Work-From-Home stats are displayed
    across the app. Only the most recently saved row is treated as active.
    """

    # One record per name — each new name stores its own settings.
    name = models.CharField(max_length=100, unique=True)
    show_wfh = models.BooleanField(
        default=True, help_text="Show Work From Home stats across the app."
    )
    per_day_salary = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Salary earned per working day.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"

    def __str__(self):
        return f"{self.name} (WFH: {'on' if self.show_wfh else 'off'})"

    @classmethod
    def get_active(cls):
        """Return the most recently used preference, or None if not onboarded."""
        return cls.objects.first()


class Attendance(models.Model):
    """A single day's attendance record, owned by one user (by name)."""

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        HALF_DAY = "HALF_DAY", "Half Day"
        LEAVE = "LEAVE", "Leave"
        WFH = "WFH", "Work From Home"

    # Each record belongs to a user (a named profile).
    user = models.ForeignKey(
        "UserPreference",
        on_delete=models.CASCADE,
        related_name="attendances",
        null=True,
    )
    date = models.DateField(help_text="The day this record is for.")
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    # Stored in hours (e.g. 8.50). Auto-calculated on save.
    total_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, editable=False
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PRESENT
    )
    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Attendance"
        verbose_name_plural = "Attendance Records"
        # One record per day per user (instead of globally unique).
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"], name="unique_user_date"
            )
        ]

    def __str__(self):
        return f"{self.date} — {self.get_status_display()}"

    def calculate_total_hours(self):
        """Return worked hours as a float from check-in/check-out times."""
        if self.check_in and self.check_out:
            today = timezone.localdate()
            start = datetime.combine(today, self.check_in)
            end = datetime.combine(today, self.check_out)
            # Handle an overnight shift (check-out past midnight).
            if end < start:
                end += timedelta(days=1)
            return round((end - start).total_seconds() / 3600, 2)
        return 0

    def save(self, *args, **kwargs):
        # Always keep total_hours in sync with the recorded times.
        self.total_hours = self.calculate_total_hours()
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        """Bootstrap/contextual colour used by the calendar + badges."""
        return {
            self.Status.PRESENT: "success",
            self.Status.ABSENT: "danger",
            self.Status.HALF_DAY: "info",
            self.Status.LEAVE: "warning",
            self.Status.WFH: "primary",
        }.get(self.status, "secondary")


class Leave(models.Model):
    """A leave application covering a date range, owned by one user."""

    class LeaveType(models.TextChoices):
        CASUAL = "CASUAL", "Casual Leave"
        SICK = "SICK", "Sick Leave"
        PERSONAL = "PERSONAL", "Personal Leave"

    class LeaveStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.ForeignKey(
        "UserPreference",
        on_delete=models.CASCADE,
        related_name="leaves",
        null=True,
    )
    leave_type = models.CharField(
        max_length=10, choices=LeaveType.choices, default=LeaveType.CASUAL
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=10, choices=LeaveStatus.choices, default=LeaveStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Leave"
        verbose_name_plural = "Leaves"

    def __str__(self):
        return f"{self.get_leave_type_display()} ({self.start_date} → {self.end_date})"

    @property
    def total_days(self):
        """Inclusive number of calendar days the leave spans."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    @property
    def status_color(self):
        return {
            self.LeaveStatus.PENDING: "warning",
            self.LeaveStatus.APPROVED: "success",
            self.LeaveStatus.REJECTED: "danger",
        }.get(self.status, "secondary")


class Expense(models.Model):
    """A single spending entry for the budget tracker, owned by one user."""

    class Category(models.TextChoices):
        FOOD = "FOOD", "Food"
        TRANSPORT = "TRANSPORT", "Transport"
        SHOPPING = "SHOPPING", "Shopping"
        BILLS = "BILLS", "Bills"
        HEALTH = "HEALTH", "Health"
        ENTERTAINMENT = "ENTERTAINMENT", "Entertainment"
        OTHER = "OTHER", "Other"

    user = models.ForeignKey(
        "UserPreference",
        on_delete=models.CASCADE,
        related_name="expenses",
        null=True,
    )
    date = models.DateField()
    category = models.CharField(
        max_length=15, choices=Category.choices, default=Category.OTHER
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def __str__(self):
        return f"{self.date} — {self.get_category_display()}: {self.amount}"

    # Hex colour used by the category chart / badges.
    CATEGORY_COLORS = {
        Category.FOOD: "#f59e0b",
        Category.TRANSPORT: "#3b82f6",
        Category.SHOPPING: "#a855f7",
        Category.BILLS: "#ef4444",
        Category.HEALTH: "#22c55e",
        Category.ENTERTAINMENT: "#06b6d4",
        Category.OTHER: "#94a3b8",
    }

    @property
    def category_color(self):
        return self.CATEGORY_COLORS.get(self.category, "#94a3b8")


class MonthlyBudget(models.Model):
    """A total spending budget a user sets for a specific month."""

    user = models.ForeignKey(
        "UserPreference",
        on_delete=models.CASCADE,
        related_name="budgets",
        null=True,
    )
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()  # 1–12
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month"]
        # One budget per month per user.
        constraints = [
            models.UniqueConstraint(
                fields=["user", "year", "month"], name="unique_user_month_budget"
            )
        ]
        verbose_name = "Monthly Budget"
        verbose_name_plural = "Monthly Budgets"

    def __str__(self):
        return f"{self.user} — {self.year}-{self.month:02d}: {self.amount}"

    @property
    def month_name(self):
        import calendar

        return calendar.month_name[self.month]
