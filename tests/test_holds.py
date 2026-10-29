from datetime import datetime, timedelta

import pytest

from crb.booking_service import BookingError, NotFound, create_booking, get_booking
from crb.db import get_db
from crb.holds import HOLD_MINUTES, confirm_hold, place_hold

START = "2030-01-15 10:00"
END = "2030-01-15 11:00"
NOW = datetime(2030, 1, 1, 9, 0, 0)


def test_hold_is_saved_with_an_expiry(app):
    with app.app_context():
        db = get_db()
        booking_id = place_hold(db, 1, 1, START, END, now=NOW)
        booking = get_booking(db, booking_id)
    assert booking["status"] == "held"
    expected = (NOW + timedelta(minutes=HOLD_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    assert booking["hold_expires_at"] == expected


def test_hold_lasts_two_minutes():
    assert HOLD_MINUTES == 2


def test_held_room_cannot_be_held_by_someone_else(app):
    with app.app_context():
        db = get_db()
        place_hold(db, 1, 1, START, END, now=NOW)
        with pytest.raises(BookingError):
            place_hold(db, 2, 1, START, END, now=NOW + timedelta(minutes=1))


def test_room_is_free_again_after_the_hold_runs_out(app):
    with app.app_context():
        db = get_db()
        place_hold(db, 1, 1, START, END, now=NOW)
        later = NOW + timedelta(minutes=HOLD_MINUTES, seconds=1)
        create_booking(db, 2, 1, START, END, now=later)


def test_confirming_a_hold_confirms_the_booking(app):
    with app.app_context():
        db = get_db()
        booking_id = place_hold(db, 1, 1, START, END, now=NOW)
        assert confirm_hold(db, booking_id, 1, now=NOW + timedelta(seconds=30)) is True
        booking = get_booking(db, booking_id)
    assert booking["status"] == "confirmed"
    assert booking["hold_expires_at"] is None


def test_confirming_twice_is_harmless(app):
    with app.app_context():
        db = get_db()
        booking_id = place_hold(db, 1, 1, START, END, now=NOW)
        confirm_hold(db, booking_id, 1, now=NOW)
        assert confirm_hold(db, booking_id, 1, now=NOW) is False


def test_confirming_after_the_hold_ran_out_fails_and_marks_it_expired(app):
    with app.app_context():
        db = get_db()
        booking_id = place_hold(db, 1, 1, START, END, now=NOW)
        with pytest.raises(BookingError):
            confirm_hold(db, booking_id, 1, now=NOW + timedelta(minutes=3))
        assert get_booking(db, booking_id)["status"] == "expired"


def test_only_the_owner_can_confirm(app):
    with app.app_context():
        db = get_db()
        booking_id = place_hold(db, 1, 1, START, END, now=NOW)
        with pytest.raises(NotFound):
            confirm_hold(db, booking_id, 2, now=NOW)
        assert get_booking(db, booking_id)["status"] == "held"


def test_unknown_booking_cannot_be_confirmed(app):
    with app.app_context():
        with pytest.raises(NotFound):
            confirm_hold(get_db(), 999, 1, now=NOW)


def test_cancelled_booking_cannot_be_confirmed(app):
    with app.app_context():
        db = get_db()
        booking_id = place_hold(db, 1, 1, START, END, now=NOW)
        db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
        db.commit()
        with pytest.raises(BookingError):
            confirm_hold(db, booking_id, 1, now=NOW)