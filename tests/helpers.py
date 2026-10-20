"""Small helpers shared by the Sprint 2 tests (they write straight to the database)."""
from werkzeug.security import generate_password_hash

from crb.db import get_db

# Seed users: 1 = employee1, 2 = admin1, 3 = auditor1
FAST_HASH = "pbkdf2:sha256:1000"  # fast hashing, tests only


def make_user(app, username, password, role="employee"):
    """Add one more user and return the new user id."""
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password, method=FAST_HASH), role),
        )
        db.commit()
        return cursor.lastrowid


def make_booking(app, room_id=1, user_id=1, start="2030-01-15 10:00", end="2030-01-15 11:00",
                 status="confirmed", series_id=None, hold_expires_at=None):
    """Insert a booking directly and return its id."""
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time, status, series_id, hold_expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (room_id, user_id, start, end, status, series_id, hold_expires_at),
        )
        db.commit()
        return cursor.lastrowid


def booking_status(app, booking_id):
    with app.app_context():
        row = get_db().execute("SELECT status FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return row["status"]


def signed_in(app, username, password):
    """A brand-new browser that is already logged in."""
    client = app.test_client()
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 302
    return client