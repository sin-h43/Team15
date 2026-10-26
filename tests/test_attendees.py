import pytest

from crb.attendees import AttendeeError, add_attendee, email_for, list_attendees
from crb.booking_service import NotFound
from crb.db import get_db
from tests.helpers import make_booking, make_user


def test_adding_an_employee_lists_them(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "employee2")
        people = list_attendees(db, booking_id)
    assert len(people) == 1
    assert people[0]["name"] == "employee2"
    assert people[0]["email"] == "employee2@crb.example"


def test_unknown_employee_is_rejected(app):
    booking_id = make_booking(app)
    with app.app_context():
        with pytest.raises(AttendeeError):
            add_attendee(get_db(), booking_id, "nobody")


def test_same_employee_cannot_be_added_twice(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "employee2")
        with pytest.raises(AttendeeError):
            add_attendee(db, booking_id, "employee2")
        assert len(list_attendees(db, booking_id)) == 1


def test_cancelled_booking_takes_no_attendees(app):
    booking_id = make_booking(app, status="cancelled")
    with app.app_context():
        with pytest.raises(AttendeeError):
            add_attendee(get_db(), booking_id, "admin1")


def test_unknown_booking_is_not_found(app):
    with app.app_context():
        with pytest.raises(NotFound):
            add_attendee(get_db(), 999, "admin1")


def test_held_booking_takes_attendees(app):
    booking_id = make_booking(app, status="held", hold_expires_at="2030-01-15 09:02:00")
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "admin1")
        assert len(list_attendees(db, booking_id)) == 1


def test_email_is_built_from_the_username():
    assert email_for("ravi") == "ravi@crb.example"