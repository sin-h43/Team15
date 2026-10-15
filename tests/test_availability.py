"""US-07 / CRB-F-012: availability check against bookings and blocks."""

import pytest

from crb.db import get_db
from crb.rooms_repo import search_available_rooms

DAY = "2026-11-01"


def _alpha_id():
    return get_db().execute(
        "SELECT id FROM rooms WHERE name = 'Alpha'"
    ).fetchone()["id"]


def _add_booking(room_id, start, end, status="confirmed"):
    db = get_db()
    user_id = db.execute(
        "SELECT id FROM users WHERE username = 'employee1'"
    ).fetchone()["id"]
    db.execute(
        "INSERT INTO bookings (room_id, user_id, start_time, end_time, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (room_id, user_id, f"{DAY} {start}", f"{DAY} {end}", status),
    )
    db.commit()


def _add_block(room_id, start, end):
    db = get_db()
    db.execute(
        "INSERT INTO maintenance_blocks (room_id, start_time, end_time, reason) "
        "VALUES (?, ?, ?, 'Maintenance')",
        (room_id, f"{DAY} {start}", f"{DAY} {end}"),
    )
    db.commit()


def _free_ids(start, end):
    rooms = search_available_rooms(f"{DAY} {start}", f"{DAY} {end}")
    return [room["id"] for room in rooms]


# (request start, request end) overlapping an existing 09:00-11:00 range
OVERLAPS = [
    ("10:00", "10:30"),  # inside
    ("08:00", "09:30"),  # overlaps the start
    ("10:30", "12:00"),  # overlaps the end
    ("08:00", "12:00"),  # surrounds it
    ("09:00", "11:00"),  # identical
]

# (request start, request end) touching but not overlapping 09:00-11:00
BACK_TO_BACK = [
    ("08:00", "09:00"),  # ends exactly when existing starts
    ("11:00", "12:00"),  # starts exactly when existing ends
]


@pytest.mark.parametrize("start,end", OVERLAPS)
def test_overlapping_booking_makes_room_unavailable(app, start, end):
    with app.app_context():
        room_id = _alpha_id()
        _add_booking(room_id, "09:00", "11:00")
        assert room_id not in _free_ids(start, end)


@pytest.mark.parametrize("start,end", BACK_TO_BACK)
def test_back_to_back_booking_does_not_overlap(app, start, end):
    with app.app_context():
        room_id = _alpha_id()
        _add_booking(room_id, "09:00", "11:00")
        assert room_id in _free_ids(start, end)


@pytest.mark.parametrize("start,end", OVERLAPS)
def test_overlapping_block_makes_room_unavailable(app, start, end):
    with app.app_context():
        room_id = _alpha_id()
        _add_block(room_id, "09:00", "11:00")
        assert room_id not in _free_ids(start, end)


@pytest.mark.parametrize("start,end", BACK_TO_BACK)
def test_back_to_back_block_does_not_overlap(app, start, end):
    with app.app_context():
        room_id = _alpha_id()
        _add_block(room_id, "09:00", "11:00")
        assert room_id in _free_ids(start, end)


def test_cancelled_booking_does_not_block_room(app):
    with app.app_context():
        room_id = _alpha_id()
        _add_booking(room_id, "09:00", "11:00", status="cancelled")
        assert room_id in _free_ids("10:00", "10:30")


def test_booking_only_affects_its_own_room(app):
    with app.app_context():
        room_id = _alpha_id()
        _add_booking(room_id, "09:00", "11:00")
        others = [r for r in _free_ids("10:00", "10:30") if r != room_id]
        assert len(others) == 4


def test_booking_on_another_day_does_not_block_room(app):
    with app.app_context():
        room_id = _alpha_id()
        _add_booking(room_id, "09:00", "11:00")
        rooms = search_available_rooms("2026-11-02 10:00", "2026-11-02 10:30")
        assert room_id in [room["id"] for room in rooms]


def test_search_api_hides_booked_room(client, login, app):
    login("employee1", "emp123")
    with app.app_context():
        room_id = _alpha_id()
        _add_booking(room_id, "09:00", "11:00")

    response = client.get(
        "/api/rooms/search",
        query_string={"date": DAY, "start": "10:00", "end": "10:30"},
    )
    assert response.status_code == 200
    assert room_id not in [r["id"] for r in response.get_json()["rooms"]]