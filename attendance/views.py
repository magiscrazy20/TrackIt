"""
Views for the attendance management app.

All attendance data is scoped to the *current user* — the named profile
active in the session (see ``context_processors.get_current_user``). Every
query filters by that user, so each name has its own attendance, payout and
preferences. Per-month statistics are computed on the fly per user.
"""

import calendar as pycalendar
import csv
import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .context_processors import SESSION_KEY, get_current_user
from .forms import ExpenseForm
from .models import Attendance, Expense, MonthlyBudget, UserPreference

MONTH_NAMES = list(pycalendar.month_name)  # ['', 'January', ... 'December']


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _month_stats(user, year, month):
    """Compute per-month attendance aggregates for one user (on the fly)."""
    qs = Attendance.objects.filter(user=user, date__year=year, date__month=month)
    S = Attendance.Status
    present = qs.filter(status=S.PRESENT).count()
    absent = qs.filter(status=S.ABSENT).count()
    leave = qs.filter(status=S.LEAVE).count()
    wfh = qs.filter(status=S.WFH).count()
    half = qs.filter(status=S.HALF_DAY).count()
    total = qs.count()
    present_equiv = present + wfh + (half * 0.5)
    pct = round((present_equiv / total) * 100, 2) if total else 0
    return {
        "present_days": present,
        "absent_days": absent,
        "leave_days": leave,
        "wfh_days": wfh,
        "half_days": half,
        "working_days": total - absent,
        "attendance_percentage": pct,
    }


def _month_payout(user, year, month):
    """Monthly payout: full pay per present day + half pay per half-day."""
    stats = _month_stats(user, year, month)
    payout = (
        Decimal(stats["present_days"]) + Decimal(stats["half_days"]) / 2
    ) * user.per_day_salary
    return payout.quantize(Decimal("0.01"))


def _selected_year_month(request):
    """Read ?year=&month= from the query string, defaulting to today."""
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        month = today.month
    month = min(max(month, 1), 12)
    return year, month


# --------------------------------------------------------------------------- #
#  Welcome / onboarding
# --------------------------------------------------------------------------- #
def welcome(request):
    """
    Landing / login page.

    Asks only for a name. An existing name signs in; a new name creates a
    profile with defaults. WFH and salary are configured on the Preferences
    page afterwards.
    """
    # Already signed in → straight to the dashboard.
    if request.method == "GET" and get_current_user(request):
        return redirect("attendance:dashboard")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if not name:
            messages.error(request, "Please enter your name to continue.")
            return render(request, "attendance/welcome.html")

        existing = UserPreference.objects.filter(name__iexact=name).first()
        if existing:
            pref = existing
            messages.success(request, f"Welcome back, {existing.name}!")
        else:
            pref = UserPreference.objects.create(
                name=name, show_wfh=False, per_day_salary=0
            )
            messages.success(request, f"Welcome, {pref.name}!")

        request.session[SESSION_KEY] = pref.pk
        return redirect("attendance:dashboard")

    return render(request, "attendance/welcome.html")


@never_cache
def preferences(request):
    """In-app Preferences page (name + WFH + per-day salary) for the current user."""
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        show_wfh = request.POST.get("show_wfh") == "yes"
        salary_raw = (request.POST.get("per_day_salary") or "").strip()
        try:
            per_day_salary = Decimal(salary_raw) if salary_raw else Decimal("0")
            if per_day_salary < 0:
                per_day_salary = Decimal("0")
        except (InvalidOperation, TypeError):
            per_day_salary = Decimal("0")

        if not name:
            messages.error(request, "Name cannot be empty.")
        elif (
            UserPreference.objects.filter(name__iexact=name)
            .exclude(pk=user.pk)
            .exists()
        ):
            messages.error(request, f"The name “{name}” is already taken.")
        else:
            user.name = name
            user.show_wfh = show_wfh
            user.per_day_salary = per_day_salary
            user.save()
            messages.success(request, "Preferences saved.")
            return redirect("attendance:preferences")

    today = timezone.localdate()
    context = {
        "active": "preferences",
        "user": user,
        "budgets": MonthlyBudget.objects.filter(user=user),
        "months": [(i, MONTH_NAMES[i]) for i in range(1, 13)],
        "years": _year_range(user),
        "current_year": today.year,
        "current_month": today.month,
    }
    return render(request, "attendance/preferences.html", context)


def set_monthly_budget(request):
    """Create or update the monthly budget for a chosen month (from Preferences)."""
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    if request.method == "POST":
        try:
            year = int(request.POST.get("year"))
            month = min(max(int(request.POST.get("month")), 1), 12)
        except (TypeError, ValueError):
            messages.error(request, "Please choose a valid month and year.")
            return redirect("attendance:preferences")

        amount_raw = (request.POST.get("amount") or "").strip()
        try:
            amount = Decimal(amount_raw) if amount_raw else Decimal("0")
            if amount < 0:
                amount = Decimal("0")
        except (InvalidOperation, TypeError):
            amount = Decimal("0")

        MonthlyBudget.objects.update_or_create(
            user=user, year=year, month=month, defaults={"amount": amount}
        )
        messages.success(request, f"Budget set for {MONTH_NAMES[month]} {year}.")
    return redirect("attendance:preferences")


def monthly_budget_delete(request, pk):
    """Delete one of the current user's monthly budgets."""
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    budget_row = get_object_or_404(MonthlyBudget, pk=pk, user=user)
    if request.method == "POST":
        budget_row.delete()
        messages.success(request, "Monthly budget removed.")
    return redirect("attendance:preferences")


def logout_view(request):
    """Sign the current user out (clear the session) and return to the landing page."""
    request.session.pop(SESSION_KEY, None)
    messages.info(request, "You have been logged out.")
    return redirect("attendance:welcome")


# --------------------------------------------------------------------------- #
#  Dashboard
# --------------------------------------------------------------------------- #
@never_cache
def dashboard(request):
    """Landing page: headline stats, monthly payout, recent records (per user)."""
    # Require a signed-in user (named profile).
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    today = timezone.localdate()
    S = Attendance.Status

    all_records = Attendance.objects.filter(user=user)
    total_logged = all_records.count()
    present_days = all_records.filter(status=S.PRESENT).count()
    absent_days = all_records.filter(status=S.ABSENT).count()
    leave_days = all_records.filter(status=S.LEAVE).count()
    wfh_days = all_records.filter(status=S.WFH).count()
    half_days = all_records.filter(status=S.HALF_DAY).count()
    # Working days = everything except absences.
    working_days = total_logged - absent_days

    present_equiv = present_days + wfh_days + (half_days * 0.5)
    attendance_pct = round((present_equiv / total_logged) * 100, 2) if total_logged else 0
    total_hours = all_records.aggregate(t=Sum("total_hours"))["t"] or 0

    # Monthly payout for this user (current month).
    per_day_salary = user.per_day_salary
    month_payout = _month_payout(user, today.year, today.month)

    context = {
        "active": "dashboard",
        "today": today,
        "total_working_days": working_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "wfh_days": wfh_days,
        "half_days": half_days,
        "total_logged": total_logged,
        "attendance_percentage": attendance_pct,
        "total_hours": total_hours,
        "current_month_name": MONTH_NAMES[today.month],
        "per_day_salary": per_day_salary,
        "month_payout": month_payout,
        "recent_records": all_records[:30],
    }
    return render(request, "attendance/dashboard.html", context)


# --------------------------------------------------------------------------- #
#  Calendar
# --------------------------------------------------------------------------- #
@never_cache
def attendance_calendar(request):
    """Monthly calendar grid with colour-coded attendance (per user)."""
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    year, month = _selected_year_month(request)

    # Build a matrix of weeks → days using Python's calendar module.
    cal = pycalendar.Calendar(firstweekday=6)  # weeks start on Sunday
    month_days = cal.monthdayscalendar(year, month)

    # Map day-of-month → attendance record for quick lookup (this user only).
    records = Attendance.objects.filter(user=user, date__year=year, date__month=month)
    by_day = {rec.date.day: rec for rec in records}

    weeks = []
    for week in month_days:
        row = []
        for day in week:
            row.append(
                {
                    "day": day,
                    # ISO date string used by the quick-mark popup (empty for padding cells).
                    "date": datetime.date(year, month, day).isoformat() if day else "",
                    "record": by_day.get(day) if day else None,
                }
            )
        weeks.append(row)

    # Previous / next month navigation.
    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year

    context = {
        "active": "calendar",
        "year": year,
        "month": month,
        "month_name": MONTH_NAMES[month],
        "weeks": weeks,
        "weekday_headers": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "today": timezone.localdate(),
        "summary": _month_stats(user, year, month),
    }
    return render(request, "attendance/calendar.html", context)


def mark_attendance(request):
    """
    Quick-mark a single day's attendance from the calendar popup.

    Accepts a POST with ``date`` (ISO), ``status`` (any of the five statuses,
    or CLEAR to remove the record) and optional ``check_in`` / ``check_out``
    times (``HH:MM``). Times let ``total_hours`` be calculated on save.
    Returns to the same month afterwards.
    """
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    if request.method == "POST":
        date_str = request.POST.get("date")
        status = request.POST.get("status")
        try:
            day = datetime.date.fromisoformat(date_str)
        except (TypeError, ValueError):
            messages.error(request, "Invalid date.")
            return redirect("attendance:calendar")

        # All five statuses can be recorded from the calendar.
        allowed = {s.value for s in Attendance.Status}

        if status == "CLEAR":
            Attendance.objects.filter(user=user, date=day).delete()
            messages.success(request, f"Cleared attendance for {day:%d %b %Y}.")
        elif status in allowed:
            # Optional check-in / check-out times (ignored if blank/invalid).
            def _parse_time(value):
                try:
                    return datetime.time.fromisoformat(value) if value else None
                except (TypeError, ValueError):
                    return None

            check_in = _parse_time(request.POST.get("check_in"))
            check_out = _parse_time(request.POST.get("check_out"))
            remarks = (request.POST.get("remarks") or "").strip()

            # Update this user's record for the day, or create it.
            Attendance.objects.update_or_create(
                user=user,
                date=day,
                defaults={
                    "status": status,
                    "check_in": check_in,
                    "check_out": check_out,
                    "remarks": remarks,
                },
            )
            label = dict(Attendance.Status.choices)[status]
            messages.success(request, f"Marked {label} for {day:%d %b %Y}.")
        else:
            messages.error(request, "Invalid status.")
            return redirect("attendance:calendar")

        return redirect(
            f"{reverse('attendance:calendar')}?year={day.year}&month={day.month}"
        )

    return redirect("attendance:calendar")


# --------------------------------------------------------------------------- #
#  CSV export
# --------------------------------------------------------------------------- #
def export_csv(request):
    """Export this user's attendance (optionally filtered by year/month) to CSV."""
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    year = request.GET.get("year")
    month = request.GET.get("month")

    qs = Attendance.objects.filter(user=user)
    if year:
        qs = qs.filter(date__year=year)
    if month:
        qs = qs.filter(date__month=month)

    filename_parts = ["attendance"]
    if year:
        filename_parts.append(str(year))
    if month:
        filename_parts.append(f"{int(month):02d}")
    filename = "_".join(filename_parts) + ".csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        ["Date", "Status", "Check In", "Check Out", "Total Hours", "Remarks"]
    )
    for rec in qs.order_by("date"):
        writer.writerow(
            [
                rec.date.strftime("%Y-%m-%d"),
                rec.get_status_display(),
                rec.check_in.strftime("%H:%M") if rec.check_in else "",
                rec.check_out.strftime("%H:%M") if rec.check_out else "",
                rec.total_hours,
                rec.remarks,
            ]
        )
    return response


# --------------------------------------------------------------------------- #
#  Budget tracker
# --------------------------------------------------------------------------- #
@never_cache
def budget(request):
    """Budget tracker: add expenses and track them against the monthly payout."""
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    year, month = _selected_year_month(request)

    # Handle "add expense" submissions.
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = user
            expense.save()
            messages.success(request, "Expense added.")
            d = expense.date
            return redirect(
                f"{reverse('attendance:budget')}?year={d.year}&month={d.month}"
            )
        messages.error(request, "Please correct the errors below.")
    else:
        # Default the date to today for convenience.
        form = ExpenseForm(initial={"date": timezone.localdate()})

    expenses = Expense.objects.filter(user=user, date__year=year, date__month=month)
    total_spent = (expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0")).quantize(
        Decimal("0.01")
    )

    # Monthly budget the user set for this month (0 if not set).
    budget_row = MonthlyBudget.objects.filter(
        user=user, year=year, month=month
    ).first()
    monthly_budget = budget_row.amount if budget_row else Decimal("0.00")
    # Remaining = budget − what's already spent this month.
    remaining = (monthly_budget - total_spent).quantize(Decimal("0.01"))

    context = {
        "active": "budget",
        "form": form,
        "year": year,
        "month": month,
        "month_name": MONTH_NAMES[month],
        "months": [(i, MONTH_NAMES[i]) for i in range(1, 13)],
        "years": _year_range(user),
        "expenses": expenses,
        "total_spent": total_spent,
        "monthly_budget": monthly_budget,
        "remaining": remaining,
    }
    return render(request, "attendance/budget.html", context)


def expense_delete(request, pk):
    """Delete one of the current user's expenses."""
    user = get_current_user(request)
    if not user:
        return redirect("attendance:welcome")

    expense = get_object_or_404(Expense, pk=pk, user=user)
    if request.method == "POST":
        d = expense.date
        expense.delete()
        messages.success(request, "Expense deleted.")
        return redirect(
            f"{reverse('attendance:budget')}?year={d.year}&month={d.month}"
        )
    return redirect("attendance:budget")


# --------------------------------------------------------------------------- #
#  Small utilities
# --------------------------------------------------------------------------- #
def _year_range(user):
    """Distinct years present in this user's data, plus the current year."""
    today = timezone.localdate()
    years = {d.year for d in Attendance.objects.filter(user=user).dates("date", "year")}
    years.add(today.year)
    return sorted(years, reverse=True)
