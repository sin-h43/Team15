"""US-14 / CRB-F-020: create booking with conflict prevention."""

import threading

import pytest

from crb.bookings_repo import BookingConflict, RoomUnavailable, create_booking
from crb.db import get_db

DAY = "2026-11-01"


def _ids():
    db = get_db()
    room = db.execute("SELECT id FROM rooms WHERE name = 'Alpha'").fetchone()["id"]
    user = db.execute("SELECT id FROM users WHERE username = 'employee1'").fetchone()["id"]
    return room, user


def _book(room, user, start, end):
    return create_booking(room, user, f"{DAY} {start}", f"{DAY} {end}")


def _count(room):
    return get_db().execute(
        "SELECT COUNT(*) FROM bookings WHERE room_id = ?", (room,)
    ).fetchone()[0]


def test_free_room_booking_is_saved(app):
    with app.app_context():
        room, user = _ids()
        booking_id = _book(room, user, "14:00", "15:00")
        row = get_db().execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        assert row["status"] == "confirmed"
        assert row["room_id"] == room


@pytest.mark.parametrize(
    "start,end",
    [("10:00", "10:30"), ("08:00", "09:30"), ("10:30", "12:00"), ("08:00", "12:00"), ("09:00", "11:00")],
)
def test_overlapping_booking_is_rejected(app, start, end):
    with app.app_context():
        room, user = _ids()
        _book(room, user, "09:00", "11:00")
        with pytest.raises(BookingConflict):
            _book(room, user, start, end)
        assert _count(room) == 1


@pytest.mark.parametrize("start,end", [("08:00", "09:00"), ("11:00", "12:00")])
def test_back_to_back_booking_is_allowed(app, start, end):
    with app.app_context():
        room, user = _ids()
        _book(room, user, "09:00", "11:00")
        _book(room, user, start, end)
        assert _count(room) == 2


def test_cancelled_booking_does_not_conflict(app):
    with app.app_context():
        room, user = _ids()
        first = _book(room, user, "09:00", "11:00")
        get_db().execute("UPDATE bookings SET status='cancelled' WHERE id=?", (first,))
        get_db().commit()
        _book(room, user, "09:30", "10:30")


def test_same_slot_in_another_room_is_allowed(app):
    with app.app_context():
        room, user = _ids()
        other = get_db().execute("SELECT id FROM rooms WHERE name='Beta'").fetchone()["id"]
        _book(room, user, "09:00", "11:00")
        _book(other, user, "09:00", "11:00")


def test_maintenance_block_rejects_booking(app):
    with app.app_context():
        room, user = _ids()
        db = get_db()
        db.execute(
            "INSERT INTO maintenance_blocks (room_id,start_time,end_time,reason) VALUES (?,?,?,'x')",
            (room, f"{DAY} 09:00", f"{DAY} 11:00"),
        )
        db.commit()
        with pytest.raises(RoomUnavailable):
            _book(room, user, "10:00", "10:30")


def test_inactive_or_missing_room_rejected(app):
    with app.app_context():
        room, user = _ids()
        get_db().execute("UPDATE rooms SET active=0 WHERE id=?", (room,))
        get_db().commit()
        with pytest.raises(RoomUnavailable):
            _book(room, user, "09:00", "10:00")
        with pytest.raises(RoomUnavailable):
            _book(9999, user, "09:00", "10:00")


def test_concurrent_requests_never_double_book(app):
    """Many threads race for one slot; exactly one may win."""
    with app.app_context():
        room, user = _ids()
    results = []
    barrier = threading.Barrier(8)

    def worker():
        with app.app_context():
            barrier.wait()
            try:
                _book(room, user, "09:00", "10:00")
                results.append("ok")
            except BookingConflict:
                results.append("conflict")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 1
    assert results.count("conflict") == 7


# ---- routes ----

def _form(room, start="14:00", end="15:00"):
    return {"room_id": room, "date": DAY, "start": start, "end": end}


def test_booking_requires_login(client):
    response = client.post("/bookings", data=_form(1))
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_route_creates_booking_and_shows_confirmation(client, login, app):
    login("employee1", "emp123")
    response = client.post("/bookings", data=_form(1), follow_redirects=True)
    assert response.status_code == 200
    assert b"Booking confirmed" in response.data


def test_route_rejects_overlap_with_conflict_message(client, login):
    login("employee1", "emp123")
    client.post("/bookings", data=_form(1, "14:00", "15:00"))
    response = client.post("/bookings", data=_form(1, "14:30", "15:30"))
    assert response.status_code == 409
    assert b"already booked" in response.data


def test_api_returns_201_then_409(client, login):
    login("employee1", "emp123")
    ok = client.post("/bookings", json=_form(1))
    assert ok.status_code == 201
    assert ok.get_json()["booking"]["status"] == "confirmed"
    clash = client.post("/bookings", json=_form(1, "14:30", "15:30"))
    assert clash.status_code == 409
    assert "already booked" in clash.get_json()["error"]


@pytest.mark.parametrize(
    "data",
    [
        {"room_id": "abc", "date": DAY, "start": "09:00", "end": "10:00"},
        {"room_id": 1, "date": "bad", "start": "09:00", "end": "10:00"},
        {"room_id": 1, "date": DAY, "start": "10:00", "end": "09:00"},
    ],
)
def test_invalid_input_returns_400(client, login, data):
    login("employee1", "emp123")
    assert client.post("/bookings", json=data).status_code == 400


def test_booking_form_page_loads(client, login):
    login("employee1", "emp123")
    assert client.get("/bookings/new?room_id=1").status_code == 200


def test_confirmation_hidden_from_other_users(client, login, app):
    login("employee1", "emp123")
    booking_id = client.post("/bookings", json=_form(1)).get_json()["booking"]["id"]
    client.post("/logout")
    login("auditor1", "aud123")
    assert client.get(f"/bookings/{booking_id}").status_code == 403