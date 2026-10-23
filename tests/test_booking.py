
from datetime import datetime

import pytest

from crb.booking_service import BookingError, NotFound, create_booking, get_booking
from crb.db import get_db
from tests.helpers import make_booking

START = "2030-01-15 10:00"
END = "2030-01-15 11:00"
NOW = datetime(2030, 1, 1, 9, 0, 0)


def count_bookings(db):
    return db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]


def test_free_room_is_booked(app):
    with app.app_context():
        db = get_db()
        booking_id = create_booking(db, 1, 1, START, END, now=NOW)
        booking = get_booking(db, booking_id)

    assert booking["status"] == "confirmed"
    assert booking["room_id"] == 1
    assert booking["user_id"] == 1
    assert booking["start_time"] == START


def test_overlapping_booking_is_rejected_and_nothing_is_saved(app):
    make_booking(app, start="2030-01-15 10:30", end="2030-01-15 11:30")

    with app.app_context():
        db = get_db()
        with pytest.raises(BookingError):
            create_booking(db, 1, 1, START, END, now=NOW)

        assert count_bookings(db) == 1


def test_back_to_back_bookings_are_allowed(app):
    make_booking(app, start="2030-01-15 09:00", end="2030-01-15 10:00")

    with app.app_context():
        db = get_db()
        create_booking(db, 1, 1, START, END, now=NOW)
        assert count_bookings(db) == 2


def test_same_time_in_another_room_is_allowed(app):
    make_booking(app, room_id=2)

    with app.app_context():
        create_booking(get_db(), 1, 1, START, END, now=NOW)


def test_maintenance_block_stops_the_booking(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO maintenance_blocks "
            "(room_id, start_time, end_time, reason) "
            "VALUES (1, '2030-01-15 09:00', "
            "'2030-01-15 12:00', 'repair')"
        )
        db.commit()

        with pytest.raises(BookingError):
            create_booking(db, 1, 1, START, END, now=NOW)


def test_unknown_room_is_rejected(app):
    with app.app_context():
        with pytest.raises(NotFound):
            create_booking(get_db(), 1, 99, START, END, now=NOW)


def test_deactivated_room_is_rejected(app):
    with app.app_context():
        db = get_db()
        db.execute("UPDATE rooms SET active = 0 WHERE id = 1")
        db.commit()

        with pytest.raises(NotFound):
            create_booking(db, 1, 1, START, END, now=NOW)


def test_booking_in_the_past_is_rejected(app):
    with app.app_context():
        with pytest.raises(BookingError):
            create_booking(
                get_db(),
                1,
                1,
                "2020-01-15 10:00",
                "2020-01-15 11:00",
                now=NOW,
            )


def test_held_booking_can_be_created_with_an_expiry(app):
    with app.app_context():
        db = get_db()
        booking_id = create_booking(
            db,
            1,
            1,
            START,
            END,
            now=NOW,
            status="held",
            hold_expires_at="2030-01-01 09:02:00",
        )
        booking = get_booking(db, booking_id)

    assert booking["status"] == "held"
    assert booking["hold_expires_at"] == "2030-01-01 09:02:00"


def test_database_is_usable_after_a_rejected_booking(app):
    make_booking(app)

    with app.app_context():
        db = get_db()
        with pytest.raises(BookingError):
            create_booking(db, 1, 1, START, END, now=NOW)

        create_booking(db, 1, 2, START, END, now=NOW)
        assert count_bookings(db) == 2
