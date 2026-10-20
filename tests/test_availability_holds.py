from datetime import datetime

from crb.availability import is_room_free
from crb.db import get_db
from tests.helpers import make_booking

START = "2030-01-15 10:00"
END = "2030-01-15 11:00"
NOW = datetime(2030, 1, 15, 9, 0, 0)


def test_hold_that_has_not_run_out_blocks_the_room(app):
    make_booking(app, status="held", hold_expires_at="2030-01-15 09:02:00")
    with app.app_context():
        assert is_room_free(get_db(), 1, START, END, now=NOW) is False


def test_hold_that_has_run_out_does_not_block_the_room(app):
    make_booking(app, status="held", hold_expires_at="2030-01-15 08:58:00")
    with app.app_context():
        assert is_room_free(get_db(), 1, START, END, now=NOW) is True


def test_expired_booking_does_not_block_the_room(app):
    make_booking(app, status="expired")
    with app.app_context():
        assert is_room_free(get_db(), 1, START, END, now=NOW) is True


def test_a_booking_does_not_clash_with_itself(app):
    booking_id = make_booking(app)
    with app.app_context():
        db = get_db()
        assert is_room_free(db, 1, START, END, now=NOW) is False
        assert is_room_free(db, 1, START, END, ignore_booking_id=booking_id, now=NOW) is True


def test_ignoring_one_booking_still_sees_the_others(app):
    mine = make_booking(app, start="2030-01-15 10:00", end="2030-01-15 10:30")
    make_booking(app, start="2030-01-15 10:30", end="2030-01-15 11:00")
    with app.app_context():
        assert is_room_free(get_db(), 1, START, END, ignore_booking_id=mine, now=NOW) is False
