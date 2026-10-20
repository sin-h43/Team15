import sqlite3

import pytest
from flask import Flask

from crb.db import close_db, get_db, init_db


def make_app(tmp_path):
    app = Flask("crb")
    app.config["DATABASE"] = str(tmp_path / "test.db")
    app.teardown_appcontext(close_db)
    return app


def add_basics(db):
    db.execute("INSERT INTO users (username, password_hash, role) VALUES ('u1', 'x', 'employee')")
    db.execute("INSERT INTO rooms (name, location, capacity) VALUES ('A', 'Pune', 4)")
    db.commit()


def test_new_tables_exist(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        rows = get_db().execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    names = [row["name"] for row in rows]
    assert "attendees" in names
    assert "outbox" in names


def test_booking_defaults(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        db = get_db()
        add_basics(db)
        db.execute(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time) "
            "VALUES (1, 1, '2030-01-01 10:00', '2030-01-01 11:00')"
        )
        row = db.execute("SELECT * FROM bookings").fetchone()
    assert row["status"] == "confirmed"
    assert row["reminder_sent"] == 0
    assert row["series_id"] is None
    assert row["created_at"] != ""


def test_unknown_booking_status_is_rejected(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        db = get_db()
        add_basics(db)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO bookings (room_id, user_id, start_time, end_time, status) "
                "VALUES (1, 1, '2030-01-01 10:00', '2030-01-01 11:00', 'maybe')"
            )


def test_same_person_cannot_be_added_twice_to_a_booking(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        db = get_db()
        add_basics(db)
        db.execute(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time) "
            "VALUES (1, 1, '2030-01-01 10:00', '2030-01-01 11:00')"
        )
        db.execute("INSERT INTO attendees (booking_id, user_id, name, email) VALUES (1, 1, 'u1', 'e')")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO attendees (booking_id, user_id, name, email) VALUES (1, 1, 'u1', 'e')")


def test_attendee_needs_an_existing_booking(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        db = get_db()
        add_basics(db)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO attendees (booking_id, user_id, name, email) VALUES (99, 1, 'u1', 'e')")