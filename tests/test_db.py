
import pytest
from flask import Flask

from crb.db import IntegrityErrors, close_db, get_db, init_db


def make_app(tmp_path):
    app = Flask("crb")
    app.config["DATABASE"] = str(tmp_path / "test.db")
    app.teardown_appcontext(close_db)
    return app


def test_init_db_creates_all_tables(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        rows = get_db().execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    names = [row["name"] for row in rows]
    for table in ["users", "rooms", "bookings", "maintenance_blocks", "audit_log"]:
        assert table in names


def test_invalid_role_is_rejected(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        with pytest.raises(IntegrityErrors):
            get_db().execute("INSERT INTO users (username, password_hash, role) VALUES ('x', 'y', 'hacker')")


def test_room_capacity_must_be_positive(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        with pytest.raises(IntegrityErrors):
            get_db().execute("INSERT INTO rooms (name, location, capacity) VALUES ('A', 'Pune', 0)")


def test_booking_needs_an_existing_room(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
        with pytest.raises(IntegrityErrors):
            get_db().execute(
                "INSERT INTO bookings (room_id, user_id, start_time, end_time) "
                "VALUES (99, 99, '2030-01-01 10:00', '2030-01-01 11:00')"
            )

def test_row_can_be_read_by_name_or_position():
    from crb.db import Row

    row = Row([("id", 7), ("name", "Alpha")])
    assert row["name"] == "Alpha" and row[0] == 7 and dict(row) == {"id": 7, "name": "Alpha"}
