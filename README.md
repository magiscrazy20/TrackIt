# Attendance Manager

A personal (single-user) **Attendance Management** web application built with
**Django 5**, **Bootstrap 5**, **Chart.js**, and **SQLite**.

Track daily office/work attendance, working hours, leaves, and attendance
statistics — with a dashboard, calendar, reports (CSV export), and analytics.

---

## Features

| Area | Highlights |
|------|-----------|
| **Dashboard** | Working / present / absent / leave / WFH counts, attendance %, total hours, current-month summary, monthly stacked bar chart, recent records |
| **Attendance** | CRUD, statuses (Present / Absent / Half Day / Leave / WFH), auto-calculated working hours, duplicate-date prevention |
| **Leaves** | CRUD, leave types (Casual / Sick / Personal), date range, status, reason |
| **Calendar** | Monthly colour-coded grid (green=present, red=absent, yellow=leave, blue=WFH, cyan=half-day) |
| **Reports** | Monthly + yearly tables, attendance %, total hours, **CSV export** |
| **Analytics** | Monthly trend (line), working-hours trend (bar), status pie/doughnut, leave statistics |
| **UI** | Responsive Bootstrap 5, sidebar navigation, stat cards, data tables, **dark-mode toggle** (persisted), search + filter + pagination |
| **Admin** | Full Django admin for all three models |
| **Data** | `seed_data` management command for realistic sample data |

## Models

- **Attendance** — `date`, `check_in`, `check_out`, `total_hours` (auto), `status`, `remarks`, `created_at`
- **Leave** — `leave_type`, `start_date`, `end_date`, `reason`, `status`, `created_at`
- **MonthlySummary** — cached per-month aggregates with a `recalculate()` method

---

## Setup

```bash
# 1. (optional) create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. install dependencies
pip install -r requirements.txt

# 3. apply database migrations
python manage.py migrate

# 4. (optional) load sample data
python manage.py seed_data --days 120
#    python manage.py seed_data --clear   # wipe + reseed

# 5. (optional) create an admin user
python manage.py createsuperuser

# 6. run the development server
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

The admin site is at <http://127.0.0.1:8000/admin/>.
A sample admin (`admin` / `admin123`) is created if you used the bundled seeder steps —
**change this password before any real deployment.**

---

## Project structure

```
AttendProject/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3                     # created after migrate
├── attendance_project/           # project package (settings, urls, wsgi, asgi)
├── attendance/                   # main app
│   ├── models.py                 # Attendance, Leave, MonthlySummary
│   ├── forms.py                  # AttendanceForm, LeaveForm
│   ├── views.py                  # CBV CRUD + dashboard/calendar/reports/analytics/csv
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   ├── management/commands/seed_data.py
│   └── templates/attendance/     # page templates
├── templates/base.html           # layout: sidebar, topbar, dark-mode
└── static/attendance/            # css/style.css, js/app.js
```

## Notes

- Working hours are calculated automatically from check-in/check-out (handles overnight shifts).
- `MonthlySummary` rows are refreshed automatically whenever attendance changes.
- Set `DEBUG = False` and configure `SECRET_KEY` / `ALLOWED_HOSTS` before deploying.
