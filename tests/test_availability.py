from crb.availability import is_room_free
from crb.db import get_db

START = "2030-01-15 10:00"
END = "2030-01-15 11:00"


def add_booking(db, room_id, start, end, status="confirmed"):
    db.execute(
        "INSERT INTO bookings (room_id, user_id, start_time, end_time, status) VALUES (?, 1, ?, ?, ?)",
        (room_id, start, end, status),
    )
    db.commit()


def add_block(db, room_id, start, end):
    db.execute(
        "INSERT INTO maintenance_blocks (room_id, start_time, end_time, reason) VALUES (?, ?, ?, 'repair')",
        (room_id, start, end),
    )
    db.commit()


def test_room_with_nothing_booked_is_free(app):
    with app.app_context():
        assert is_room_free(get_db(), 1, START, END) is True


def test_overlapping_booking_makes_room_busy(app):
    with app.app_context():
        db = get_db()
        add_booking(db, 1, "2030-01-15 10:30", "2030-01-15 11:30")
        assert is_room_free(db, 1, START, END) is False


def test_booking_that_contains_the_request_makes_room_busy(app):
    with app.app_context():
        db = get_db()
        add_booking(db, 1, "2030-01-15 09:00", "2030-01-15 12:00")
        assert is_room_free(db, 1, START, END) is False


def test_booking_ending_exactly_at_start_is_not_an_overlap(app):
    with app.app_context():
        db = get_db()
        add_booking(db, 1, "2030-01-15 09:00", "2030-01-15 10:00")
        assert is_room_free(db, 1, START, END) is True


def test_booking_starting_exactly_at_end_is_not_an_overlap(app):
    with app.app_context():
        db = get_db()
        add_booking(db, 1, "2030-01-15 11:00", "2030-01-15 12:00")
        assert is_room_free(db, 1, START, END) is True


def test_cancelled_booking_does_not_block_the_room(app):
    with app.app_context():
        db = get_db()
        add_booking(db, 1, START, END, status="cancelled")
        assert is_room_free(db, 1, START, END) is True


def test_booking_in_another_room_does_not_matter(app):
    with app.app_context():
        db = get_db()
        add_booking(db, 2, START, END)
        assert is_room_free(db, 1, START, END) is True


def test_maintenance_block_makes_room_busy(app):
    with app.app_context():
        db = get_db()
        add_block(db, 1, "2030-01-15 09:00", "2030-01-15 10:30")
        assert is_room_free(db, 1, START, END) is False


def test_maintenance_block_on_another_day_does_not_matter(app):
    with app.app_context():
        db = get_db()
        add_block(db, 1, "2030-01-16 09:00", "2030-01-16 17:00")
        assert is_room_free(db, 1, START, END) is True
