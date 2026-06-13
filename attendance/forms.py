"""Forms for attendance, leave and budget management with Bootstrap 5 styling."""

from django import forms

from .models import Attendance, Expense, Leave


class ExpenseForm(forms.ModelForm):
    """Add / edit a budget expense."""

    class Meta:
        model = Expense
        fields = ["date", "category", "amount", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "0.00",
                    "inputmode": "decimal",
                }
            ),
            "note": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Optional note"}
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount


class AttendanceForm(forms.ModelForm):
    """Create/edit a daily attendance record."""

    class Meta:
        model = Attendance
        fields = ["date", "check_in", "check_out", "status", "remarks"]
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "check_in": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "check_out": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "remarks": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Optional remarks"}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")

        # Prevent duplicate attendance for the same date (on create + edit).
        if date:
            qs = Attendance.objects.filter(date=date)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "date", "An attendance record already exists for this date."
                )

        # check_out must be after check_in for a same-day shift.
        if check_in and check_out and check_out <= check_in:
            self.add_error(
                "check_out", "Check-out time must be later than check-in time."
            )
        return cleaned


class LeaveForm(forms.ModelForm):
    """Apply for / edit a leave."""

    class Meta:
        model = Leave
        fields = ["leave_type", "start_date", "end_date", "reason", "status"]
        widgets = {
            "leave_type": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "reason": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Reason for leave"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before the start date.")
        return cleaned
