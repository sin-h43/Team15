# Conference Room Booking (CRB)

A small web app for booking conference rooms, built for the Software Engineering course
(Python, Flask and SQLite, with optional Postgres for hosting). Requirements: `CRB_SRS.docx`. Design: `CRB_SAD.docx`. Tests: `CRB_Test_Plan.docx`.

## Run it

```bash
python -m venv venv
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
flask --app crb.app init-db      # creates crb.db with demo data (wipes old data!)
flask --app crb.app run          # open http://127.0.0.1:5000
```

## Demo accounts

| Username   | Password   | Role     | Can do                                                          |
|------------|------------|----------|-----------------------------------------------------------------|
| employee1  | emp123     | employee | search, book, add attendees, move, cancel, recurring bookings   |
| admin1     | admin123   | admin    | everything above for any booking, plus rooms, blocks, audit log, report, sent emails |
| auditor1   | aud123     | auditor  | read-only: audit log and bookings                               |

## Real accounts

- Anyone can **Sign up** (username, email, password of at least 8 characters). The account stays inactive until
  the emailed confirmation link is opened. **Forgot password?** works the same way (link valid for 1 hour).
- Emails are always saved in the outbox, and are really sent when `RESEND_API_KEY` is set (see `docs/DEPLOYMENT.md`). Without it: log in as `admin1` and open **Sent emails**,
  or read the link printed in the terminal where `flask run` is running.
- New sign-ups are employees. An admin changes roles on the **Users** page.
- Log in with either username or email. Attendees can be invited by username or email.
- Create a confirmed account (for example the first admin on a fresh database) with
  `flask --app crb.app create-user`.

## Live availability

The room search refreshes itself every few seconds, so a room someone else just booked disappears
and a freed room appears without reloading. A held booking shows a countdown and reloads when the
hold runs out. (Updates are polled from `/rooms/search?...&format=json`, which also works on hosts
without long-lived connections.)

## Demo script (5 minutes)

1. Log in as `employee1`, open **Search rooms**, search a day and click **Book** on a room. (Optional: **Sign up** a new user first and confirm the email from **Sent emails**.)
2. On the booking page the room is held for 2 minutes. Add an attendee (`admin1`), then **Confirm booking**.
3. Log in as `admin1`: **Sent emails** shows the confirmation sent to both people.
4. Open the booking, **Move** it to another time, then **Cancel** it. Check **Sent emails** and **Audit log**.
5. Open **Recurring booking**, book a daily series and cancel one date.
6. Open **Utilisation report** for the month.

## Background jobs (run from a terminal)

```bash
flask --app crb.app send-reminders   # emails people whose meeting starts within 10 minutes
flask --app crb.app purge-old-logs   # removes audit log rows older than 2 years
```

## Run the tests

```bash
python -m pytest
```

The suite also runs on Postgres; see `docs/DEPLOYMENT.md`.

## Where things live

| Module (SAD)         | Files                                                                                  | Requirements |
|----------------------|----------------------------------------------------------------------------------------|--------------|
| Foundation           | `crb/app.py`, `crb/db.py`, `crb/schema.sql`, `crb/seed.py`, `crb/validators.py`        | CRB-SR-005   |
| Auth & Access        | `crb/guards.py`, `crb/lockout.py`, `crb/auth.py`, `crb/audit.py`, `crb/security.py`, `crb/crypto.py`, `crb/retention.py` | CRB-F-001/002/003, CRB-SR-001/002/003/004/006, CRB-NF-004 |
| Booking Engine       | `crb/availability.py`, `crb/equipment.py`, `crb/search*.py`, `crb/booking_service.py`, `crb/holds.py`, `crb/hold_cleanup.py`, `crb/booking_routes.py`, `crb/bookings_view.py`, `crb/cancellation.py`, `crb/cancel_routes.py`, `crb/reschedule*.py`, `crb/attendees.py`, `crb/attendee_routes.py` | CRB-F-010/011/012/020/021/022/023/030/031/032 |
| Recurring bookings   | `crb/recurring.py`, `crb/recurring_routes.py`                                          | CRB-F-040/041 |
| Room/Resource Admin  | `crb/rooms_repo.py`, `crb/blocks_repo.py`, `crb/admin_routes.py`                        | CRB-F-050/051 |
| Notifications and reports | `crb/notifications.py`, `crb/cancel_notice.py`, `crb/reminders.py`, `crb/notify_routes.py`, `crb/reports.py`, `crb/report_routes.py` | CRB-F-060/061/062/070 |
| Accounts, email, deployment | `crb/accounts.py`, `crb/tokens.py`, `crb/user_admin_routes.py`, `crb/mailer.py`, `crb/ratelimit.py`, `crb/cron_routes.py`, `app.py`, `public/static/` | CRB-F-001/002, CRB-F-060/061/062, CRB-SR-001/004/005 |

## Known limits

- Set `DATABASE_URL` to use Postgres instead of the SQLite file. Hosting on Vercel + Neon is described in `docs/DEPLOYMENT.md` (the deployment itself has not been tried).
- Login uses accounts created in this app (sign-up with email confirmation), not company single sign-on.
- Emails are saved in the `outbox` table (**Sent emails** page). Real delivery needs `RESEND_API_KEY`; without it no mail leaves the machine.
- HTTPS needs a certificate; see `docs/DEPLOYMENT.md`.
- Availability, load and "new office by configuration" targets (CRB-NF-002/003/006) are design goals, not tested here.

## Sprint status

- Sprint 1 (12-21 Oct): login, roles, lockout, audit log, room search, room admin, maintenance blocks, booking, booking ID, attendees.
- Sprint 2 (22-31 Oct): holds, cancel, reschedule, recurring bookings, notifications, report, security hardening, release `v1.0`.