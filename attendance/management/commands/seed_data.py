"""
Sample data seeder.

Usage:
    python manage.py seed_data                  # seed ~last 90 days for "Demo"
    python manage.py seed_data --days 180        # custom range
    python manage.py seed_data --name Pablo      # seed for a specific user
    python manage.py seed_data --clear           # wipe this user's data first
"""

import datetime
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from attendance.models import Attendance, Leave, UserPreference


class Command(BaseCommand):
    help = "Seed the database with realistic sample attendance and leave data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of past days to generate attendance for (default: 90).",
        )
        parser.add_argument(
            "--name",
            type=str,
            default="Demo",
            help="Name of the user profile to seed data for (default: Demo).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete this user's existing attendance/leave data before seeding.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        # All seeded data belongs to one named user profile.
        user, _ = UserPreference.objects.get_or_create(
            name=options["name"],
            defaults={"show_wfh": True, "per_day_salary": 1000},
        )

        if options["clear"]:
            Attendance.objects.filter(user=user).delete()
            Leave.objects.filter(user=user).delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared existing data for {user.name}.")
            )

        today = timezone.localdate()
        statuses = (
            [Attendance.Status.PRESENT] * 12
            + [Attendance.Status.WFH] * 4
            + [Attendance.Status.LEAVE] * 2
            + [Attendance.Status.HALF_DAY] * 1
            + [Attendance.Status.ABSENT] * 1
        )

        created = 0
        for offset in range(days):
            day = today - datetime.timedelta(days=offset)
            # Skip weekends for a realistic office pattern.
            if day.weekday() >= 5:
                continue
            if Attendance.objects.filter(user=user, date=day).exists():
                continue

            status = random.choice(statuses)
            check_in = check_out = None
            remarks = ""

            if status in (Attendance.Status.PRESENT, Attendance.Status.WFH):
                in_h = random.choice([9, 9, 10])
                in_m = random.choice([0, 15, 30, 45])
                check_in = datetime.time(in_h, in_m)
                out_h = random.choice([17, 18, 18, 19])
                out_m = random.choice([0, 15, 30, 45])
                check_out = datetime.time(out_h, out_m)
                if status == Attendance.Status.WFH:
                    remarks = "Worked remotely."
            elif status == Attendance.Status.HALF_DAY:
                check_in = datetime.time(9, 30)
                check_out = datetime.time(13, 30)
                remarks = "Half day."
            elif status == Attendance.Status.LEAVE:
                remarks = "On leave."
            else:  # ABSENT
                remarks = "Absent."

            Attendance.objects.create(
                user=user,
                date=day,
                check_in=check_in,
                check_out=check_out,
                status=status,
                remarks=remarks,
            )
            created += 1

        # A few sample leave applications.
        leave_samples = [
            (
                Leave.LeaveType.CASUAL,
                today - datetime.timedelta(days=20),
                today - datetime.timedelta(days=19),
                "Family function.",
                Leave.LeaveStatus.APPROVED,
            ),
            (
                Leave.LeaveType.SICK,
                today - datetime.timedelta(days=10),
                today - datetime.timedelta(days=10),
                "Fever and rest.",
                Leave.LeaveStatus.APPROVED,
            ),
            (
                Leave.LeaveType.PERSONAL,
                today + datetime.timedelta(days=5),
                today + datetime.timedelta(days=6),
                "Personal errands.",
                Leave.LeaveStatus.PENDING,
            ),
        ]
        for lt, start, end, reason, status in leave_samples:
            Leave.objects.get_or_create(
                user=user,
                leave_type=lt,
                start_date=start,
                end_date=end,
                defaults={"reason": reason, "status": status},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} attendance records and "
                f"{len(leave_samples)} leaves for {user.name}."
            )
        )
