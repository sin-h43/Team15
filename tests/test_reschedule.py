from datetime import datetime

import pytest

from crb.booking_service import BookingError, NotAllowed, NotFound, get_booking
from crb.db import get_db
from crb.reschedule import reschedule_booking
from tests.helpers import make_booking, make_user

NOW = datetime(2030, 1, 1, 9, 0, 0)


def move(app, booking_id, user_id=1, role="employee", room_id=1,
         start="2030-01-16 14:00", end="2030-01-16 15:00"):
    with app.app_context():
        reschedule_booking(get_db(), booking_id, user_id, role, room_id, start, end, now=NOW)


def row(app, booking_id):
    with app.app_context():
        return get_booking(get_db(), booking_id)


def test_booking_moves_to_a_free_time(app):
    booking_id = make_booking(app)
    move(app, booking_id)
    moved = row(app, booking_id)
    assert moved["start_time"] == "2030-01-16 14:00"
    assert moved["end_time"] == "2030-01-16 15:00"
    assert moved["room_id"] == 1


def test_booking_moves_to_another_room(app):
    booking_id = make_booking(app)
    move(app, booking_id, room_id=3, start="2030-01-15 10:00", end="2030-01-15 11:00")
    assert row(app, booking_id)["room_id"] == 3


def test_booking_can_shift_into_its_own_old_slot(app):
    booking_id = make_booking(app)
    move(app, booking_id, start="2030-01-15 10:30", end="2030-01-15 11:30")
    assert row(app, booking_id)["start_time"] == "2030-01-15 10:30"


def test_taken_slot_is_rejected_and_the_old_booking_stays(app):
    booking_id = make_booking(app)
    make_booking(app, user_id=2, start="2030-01-16 14:00", end="2030-01-16 15:00")
    with pytest.raises(BookingError):
        move(app, booking_id)
    assert row(app, booking_id)["start_time"] == "2030-01-15 10:00"


def test_other_employee_cannot_move_it(app):
    booking_id = make_booking(app)
    other = make_user(app, "employee2", "emp234")
    with pytest.raises(NotAllowed):
        move(app, booking_id, user_id=other)
    assert row(app, booking_id)["start_time"] == "2030-01-15 10:00"


def test_admin_can_move_any_booking(app):
    booking_id = make_booking(app)
    move(app, booking_id, user_id=2, role="admin")
    assert row(app, booking_id)["start_time"] == "2030-01-16 14:00"


def test_cancelled_booking_cannot_be_moved(app):
    booking_id = make_booking(app, status="cancelled")
    with pytest.raises(BookingError):
        move(app, booking_id)


def test_time_in_the_past_is_rejected(app):
    booking_id = make_booking(app)
    with pytest.raises(BookingError):
        move(app, booking_id, start="2020-01-16 14:00", end="2020-01-16 15:00")


def test_unknown_booking_and_unknown_room(app):
    booking_id = make_booking(app)
    with pytest.raises(NotFound):
        move(app, 999)
    with pytest.raises(NotFound):
        move(app, booking_id, room_id=99)


def test_reminder_flag_is_reset_when_moved(app):
    booking_id = make_booking(app)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE bookings SET reminder_sent = 1 WHERE id = ?", (booking_id,))
        db.commit()
    move(app, booking_id)
    assert row(app, booking_id)["reminder_sent"] == 0