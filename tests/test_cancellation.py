import pytest

from crb.availability import is_room_free
from crb.booking_service import BookingError, NotAllowed, NotFound
from crb.cancellation import cancel_booking
from crb.db import get_db
from tests.helpers import booking_status, make_booking, make_user

START = "2030-01-15 10:00"
END = "2030-01-15 11:00"


def test_owner_can_cancel(app):
    booking_id = make_booking(app)
    with app.app_context():
        cancel_booking(get_db(), booking_id, 1, "employee")
    assert booking_status(app, booking_id) == "cancelled"


def test_admin_can_cancel_someone_elses_booking(app):
    booking_id = make_booking(app)
    with app.app_context():
        cancel_booking(get_db(), booking_id, 2, "admin")
    assert booking_status(app, booking_id) == "cancelled"


def test_other_employee_cannot_cancel(app):
    booking_id = make_booking(app)
    other = make_user(app, "employee2", "emp234")
    with app.app_context():
        with pytest.raises(NotAllowed):
            cancel_booking(get_db(), booking_id, other, "employee")
    assert booking_status(app, booking_id) == "confirmed"


def test_auditor_cannot_cancel(app):
    booking_id = make_booking(app)
    with app.app_context():
        with pytest.raises(NotAllowed):
            cancel_booking(get_db(), booking_id, 3, "auditor")


def test_cancelling_twice_is_an_error(app):
    booking_id = make_booking(app)
    with app.app_context():
        db = get_db()
        cancel_booking(db, booking_id, 1, "employee")
        with pytest.raises(BookingError):
            cancel_booking(db, booking_id, 1, "employee")


def test_unknown_booking_is_not_found(app):
    with app.app_context():
        with pytest.raises(NotFound):
            cancel_booking(get_db(), 999, 1, "employee")


def test_cancelled_room_is_free_again(app):
    booking_id = make_booking(app)
    with app.app_context():
        db = get_db()
        assert is_room_free(db, 1, START, END) is False
        cancel_booking(db, booking_id, 1, "employee")
        assert is_room_free(db, 1, START, END) is True


def test_a_hold_can_be_cancelled(app):
    booking_id = make_booking(app, status="held", hold_expires_at="2030-01-15 09:02:00")
    with app.app_context():
        cancel_booking(get_db(), booking_id, 1, "employee")
    assert booking_status(app, booking_id) == "cancelled"
