import time

import pytest

from crb.db import get_db
from crb.search import find_rooms

START = "2031-03-10 10:00"
END = "2031-03-10 11:00"


def fill_with_bookings(app, count=1000):
    """About `count` confirmed bookings spread over the five demo rooms and many days."""
    rows = []
    for number in range(count):
        day = 1 + number % 300
        year = 2030 + day // 365
        stamp = "%d-%02d-%02d" % (year, 1 + (day % 365) // 31, 1 + (day % 365) % 28)
        rows.append((1 + number % 5, 1, stamp + " 08:00", stamp + " 09:00"))
    with app.app_context():
        db = get_db()
        db.executemany(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time) VALUES (?, ?, ?, ?)", rows
        )
        db.commit()


def test_search_stays_under_two_seconds_with_a_thousand_bookings(app):
    fill_with_bookings(app)
    with app.app_context():
        db = get_db()
        started = time.perf_counter()
        for _ in range(20):
            find_rooms(db, START, END)
        average = (time.perf_counter() - started) / 20
    assert average < 2.0


def test_availability_query_uses_the_room_and_time_index(app):
    with app.app_context():
        if get_db().postgres:
            pytest.skip("EXPLAIN QUERY PLAN is SQLite-only; Postgres plans depend on table size")
        plan = get_db().execute(
            "EXPLAIN QUERY PLAN SELECT 1 FROM bookings WHERE room_id = ? AND start_time < ? AND end_time > ?",
            (1, END, START),
        ).fetchall()
    assert "idx_bookings_room_time" in " ".join(row["detail"] for row in plan)


def test_maintenance_query_uses_its_index(app):
    with app.app_context():
        if get_db().postgres:
            pytest.skip("EXPLAIN QUERY PLAN is SQLite-only; Postgres plans depend on table size")
        plan = get_db().execute(
            "EXPLAIN QUERY PLAN SELECT 1 FROM maintenance_blocks WHERE room_id = ? AND start_time < ? AND end_time > ?",
            (1, END, START),
        ).fetchall()
    assert "idx_blocks_room_time" in " ".join(row["detail"] for row in plan)