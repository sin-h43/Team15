# Conference Room Booking (CRB)

A web application for booking conference rooms across office locations, built by Team 15 for the
Software Engineering course. People search for a free room, book it without clashes, invite attendees and
get email confirmations and reminders. Admins manage rooms, maintenance, users and reports.

- **Live site:** https://crb-team15.vercel.app
- **Requirements:** `CRB_Team15_SRS.docx` (33 requirements: CRB-F, CRB-NF, CRB-SR)
- **Design:** `CRB_Team15_SAD.docx` (architecture, STRIDE threat model, decision records ADR-01/07/08/09)
- **Testing:** `CRB_Team15_Test_Plan.docx`
- **Deployment guide:** `docs/DEPLOYMENT.md`

## Features

| For | What it does |
|-----|--------------|
| Everyone | Sign up with email confirmation, log in with username or email, reset a forgotten password by email, lockout after 5 wrong passwords, 30-minute idle timeout, high-contrast mode |
| Employees | Search rooms by location, date, time, capacity and equipment (results refresh live every 5 seconds); book with a 2-minute hold and countdown; add attendees; move, edit or cancel a booking; daily or weekly recurring series with an optional end date |
| Admins | Everything above for any booking, plus rooms (add, edit, deactivate), maintenance blocks, users and roles, **Confirm now** for accounts whose email did not arrive, utilisation report, sent-emails page, audit log |
| Auditors | Read-only audit log and bookings |
| Email | Confirmation, change, cancellation and 10-minute reminder emails (sent through Resend; every email is also kept in an outbox with a status) |

## Technology

Python 3 and Flask (one Blueprint per feature) · server-rendered Jinja templates with one stylesheet and small
JavaScript files · SQLite locally and in tests, PostgreSQL (Neon) in production · Resend for email ·
pytest for testing · hosted on Vercel.

**Architecture:** a layered, modular monolith (close to MVC): templates → routes (Blueprints) → services
(booking rules) → data access (`crb/db.py`, which runs the same SQL on SQLite or PostgreSQL). The SAD explains
the architecture and the reasons behind each decision.

## Run it on your computer

```bash
python -m venv venv
# Windows:   venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
flask --app crb.app init-db      # creates crb.db with demo users and rooms (wipes old local data!)
flask --app crb.app run          # open http://127.0.0.1:5000
```

Locally there is no mail service, so emails go to the **Sent emails** page (log in as `admin1`) and sign-up or
reset links are also printed in the terminal running `flask run`.

### Demo accounts (local database only)

| Username  | Password | Role     | Can do |
|-----------|----------|----------|--------|
| employee1 | emp123   | employee | search, book, attendees, move, cancel, recurring bookings |
| admin1    | admin123 | admin    | everything above for any booking, plus rooms, maintenance, users, report, sent emails, audit log |
| auditor1  | aud123   | auditor  | read-only: audit log and bookings |

These accounts are **not** on the live site; its database was created empty and its admin was made with
`create-user`.

## Run the tests

```bash
pip install -r requirements-dev.txt   # once, inside your virtual environment
python -m pytest                      # expect: 372 passed
```

Handy options: `python -m pytest -q` (short output), `python -m pytest tests/test_booking.py` (one file),
`python -m pytest -k recurring` (by name), `python -m pytest -x` (stop at first failure).

The tests use their own temporary databases and a fake mail service: they never touch `crb.db`, the live
database or real email. The same suite also runs on PostgreSQL; see "Running the tests on Postgres" in
`docs/DEPLOYMENT.md`.

## Command-line tools

```bash
flask --app crb.app init-db                  # create tables + demo data (wipes data; asks first on Postgres)
flask --app crb.app init-db --empty --yes    # tables only, no demo users (use for a real database)
flask --app crb.app create-user --role admin # create a confirmed account, e.g. the first admin
flask --app crb.app send-reminders           # send reminders for meetings starting within 10 minutes
flask --app crb.app purge-old-logs           # delete audit log rows older than 2 years
```

## Configuration (environment variables)

Nothing is required to run locally. In production (Vercel) these are set in the project settings:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL address (Neon). Without it the app uses the local `crb.db` SQLite file |
| `CRB_SECRET_KEY` | Long random value; signs login cookies and is the key for encrypted attendee data |
| `CRB_HTTPS`, `CRB_TRUST_PROXY` | `1` on the live site: secure cookies, HSTS, real client address behind Vercel |
| `CRB_TIMEZONE` | e.g. `Asia/Kolkata`; servers run on UTC, users type local times |
| `RESEND_API_KEY`, `CRB_MAIL_FROM` | Real email delivery and the sender address |
| `CRON_SECRET` | Protects `/cron/send-reminders`, which cron-job.org calls every minute |
| `CRB_RECURRING_HORIZON_DAYS` | Optional; how far ahead a recurring series may run (default 90) |

Never commit secrets. `.env` files are ignored by git.

## Deployment

The live site runs on **Vercel** (the Flask app as a serverless function, static files from `public/static/`),
with a **Neon** PostgreSQL database, **Resend** for email and **cron-job.org** for the 10-minute reminders.
Vercel is not linked to GitHub, so a new version goes live only when someone runs, from the project folder:

```bash
vercel deploy --prod --yes
```

Full step-by-step setup is in `docs/DEPLOYMENT.md`.

## Demo script (5 minutes)

1. On the live site, **Sign up** a new user in a second browser. As `admin1`, open **Users** and click
   **Confirm now** for them (only the Resend account owner receives real email; see Known limits).
2. **Search rooms**: pick a date and time; the results refresh by themselves.
3. Click **Book**: the room is held for 2 minutes with a countdown. Add an attendee, then **Confirm booking**.
   The confirmation email arrives; in the other browser the booked room disappears from the search.
4. **Move** the booking to another time, then **Cancel** it. Check **Sent emails** and the **Audit log**.
5. **Recurring**: book a daily series with a **Repeat until** date, then cancel one occurrence.
6. Admin: add a room, add a maintenance block, open the **Utilisation report**.
7. Click **High contrast** in the header to show the accessibility mode.

## Where things live

| Area | Files | Requirements |
|------|-------|--------------|
| Foundation | `crb/app.py`, `crb/db.py`, `crb/schema.sql`, `crb/seed.py`, `crb/validators.py`, `crb/clock.py`, `app.py` (Vercel entry) | CRB-SR-005 |
| Auth and access | `crb/auth.py`, `crb/accounts.py`, `crb/tokens.py`, `crb/guards.py`, `crb/lockout.py`, `crb/user_admin_routes.py` | CRB-F-001/002/003, CRB-SR-002/004 |
| Security | `crb/security.py`, `crb/crypto.py`, `crb/ratelimit.py`, `crb/audit.py`, `crb/retention.py` | CRB-SR-001/003/005/006, CRB-NF-004 |
| Search | `crb/search.py`, `crb/search_routes.py`, `crb/availability.py`, `crb/equipment.py` | CRB-F-010/011/012, CRB-NF-001 |
| Booking engine | `crb/booking_service.py`, `crb/holds.py`, `crb/hold_cleanup.py`, `crb/booking_routes.py`, `crb/bookings_view.py`, `crb/booking_code.py` | CRB-F-020/021/023/032 |
| Changes | `crb/cancellation.py`, `crb/cancel_routes.py`, `crb/reschedule.py`, `crb/reschedule_routes.py` | CRB-F-030/031/041 |
| Recurring | `crb/recurring.py`, `crb/recurring_routes.py` | CRB-F-040/041 |
| Attendees | `crb/attendees.py`, `crb/attendee_routes.py` | CRB-F-022 |
| Room admin | `crb/rooms_repo.py`, `crb/blocks_repo.py`, `crb/admin_routes.py` | CRB-F-050/051, CRB-NF-006 |
| Notifications | `crb/notifications.py`, `crb/mailer.py`, `crb/cancel_notice.py`, `crb/reminders.py`, `crb/cron_routes.py`, `crb/notify_routes.py` | CRB-F-060/061/062 |
| Reports | `crb/reports.py`, `crb/report_routes.py` | CRB-F-070 |
| UI | `crb/templates/`, `public/static/style.css`, `live.js`, `contrast.js` | CRB-NF-005 |
| Tests | `tests/` (52 files, 372 tests) | all |

## Requirements status

31 of the 33 SRS requirements are implemented and tested. The other two, CRB-NF-002 (99.5% availability) and
CRB-NF-003 (500 concurrent users), are operational targets that need uptime monitoring and a load test on
production. The traceability matrix (RTM) in the SRS links every requirement to its tests.

## Known limits

- **Email to other people:** without a verified domain, Resend only delivers to the email address of the Resend
  account owner. Everyone else can still use the site; an admin activates their account with **Confirm now**.
- **Login:** accounts are created in this app (sign-up with email confirmation), not company single sign-on.
- **Deploys are manual:** Vercel is not connected to GitHub, and there is no automated CI yet; tests are run
  locally before each push and every change goes through a reviewed pull request.
- **Not measured:** availability and load targets (CRB-NF-002/003), an independent TLS scan and a full
  accessibility audit.

## Troubleshooting

- **`CRB_TIMEZONE is not a valid timezone name`** when running tests: your virtual environment is missing
  timezone data. Run `pip install -r requirements-dev.txt`.
- **Pages show without styling:** an old copy of the server is still running on port 5000. Stop it or run
  `flask --app crb.app run --port 5050`, then press Ctrl+F5.
- **No rooms in search on a new database:** expected; an admin adds rooms under **Rooms → Add New Room**.
- **A friend's confirmation email never arrives:** see "Email to other people" above.

## Team and sprints

| Member | Track | Main work |
|--------|-------|-----------|
| Sinchana K | Auth and access | login/logout, role guards, lockout, audit log, booking pages, cancellation, attendee encryption, log retention, security headers |
| Pavan D C | Booking engine | room search and filters, availability check, conflict-free booking, 2-minute hold, reschedule, expired holds |
| Dishanth Gowda H D | Room and resource admin | room admin, maintenance blocks, recurring bookings and single-occurrence edits |
| Diran Somanna | Notifications and integration | scaffold, database, validators, attendees, emails and reminders, report, release work (accounts, real email, PostgreSQL, live updates, deployment) |

- **Sprint 1 (12-21 Oct):** login, roles, lockout, audit log, room search, room admin, maintenance blocks,
  booking, booking ID, attendees.
- **Sprint 2 (22-31 Oct):** holds, cancel, reschedule, recurring bookings, notifications, report, security.
- **Release (Nov):** UI redesign, CSRF, self-signup with email confirmation, real email, PostgreSQL, live
  availability, time-zone fix, Vercel deployment, admin account confirmation, recurring end date, high-contrast
  mode.

Workflow: one branch and one pull request per change, peer review before merging with a merge commit, and the
full test suite run before every push.
