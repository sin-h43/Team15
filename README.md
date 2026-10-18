# Enterprise Conference Room Booking System
***Context & Core Problem***

Educational institutions and corporate organizations face frequent resource allocation bottlenecks, including scheduling conflicts, "ghost bookings" (reserved rooms left empty), and inefficient space utilization. A multi-user booking system must handle high-concurrency requests, enforce role-based access rules, manage physical amenities (projectors, video conferencing kits, seating capacity), and prevent race conditions where two users attempt to reserve the same slot simultaneously.

**Core Deliverables**

- Real-time Schedule Matrix: Grid-based visualization of room availability across locations, floors, and time slots.
- Concurrency-Safe Booking Engine: Transactional booking mechanism with database locks to ensure zero double-bookings.
- Role-Based Access Control (RBAC): Tiered roles (Students/Employees, Faculty/Leads, Facilities Admin) with booking duration limits and approval workflows.
- Lifecycle Management: Auto-release triggers for no-shows (check-in within 10 minutes), recurring reservations, and calendar synchronization (iCal/Google Calendar).

## Tech stack

Python 3, Flask, SQLite, pytest.

## Run it

```bash
python -m venv venv
# Windows:   venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
flask --app crb.app init-db
flask --app crb.app run
```

init-db creates crb.db with demo data and wipes any old data. The app runs at http://127.0.0.1:5000

## Demo accounts

| Username  | Password | Role     | Can do                                    |
|-----------|----------|----------|-------------------------------------------|
| employee1 | emp123   | employee | search rooms                              |
| admin1    | admin123 | admin    | manage rooms, block rooms, read audit log |
| auditor1  | aud123   | auditor  | read audit log                            |

## Run the tests

```bash
python -m pytest
```

## Where things live

| Area                 | Files                                                           |
|----------------------|-----------------------------------------------------------------|
| Foundation           | crb/app.py, crb/db.py, crb/schema.sql, crb/seed.py, crb/validators.py |
| Auth and access      | crb/guards.py, crb/lockout.py, crb/auth.py, crb/audit.py        |
| Room search          | crb/search_routes.py, crb/equipment.py, crb/rooms_repo.py       |
| Room and block admin | crb/admin_routes.py, crb/blocks_repo.py                         |
| Bookings (Sprint 2)  | crb/booking_routes.py, crb/bookings_repo.py                     |

Project documents: CRB_Team15_SRS.docx, CRB_Team15_SAD.pdf, CRB_Team15_Test_Plan.pdf

## Sprint status

- Sprint 1 (11-17 Oct): login, roles, lockout, audit log, room search, room admin, maintenance blocks
- Sprint 2 (18-24 Oct): booking creation, conflict detection, holds, attendees, reschedule, cancel
- Sprint 3 (25-31 Oct): recurring bookings, notifications, utilization report, hardening
