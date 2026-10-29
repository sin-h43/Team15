from datetime import datetime

from crb.attendees import add_attendee
from crb.db import get_db
from crb.notifications import describe_booking, notify_booking_created, recipients, send_email
from tests.helpers import make_booking, make_user


def outbox(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM outbox ORDER BY id").fetchall()


def test_send_email_saves_a_row(app):
    with app.app_context():
        send_email(get_db(), "employee1", "Hello", "Body text", now=datetime(2030, 1, 1, 9, 0, 0))
    rows = outbox(app)
    assert len(rows) == 1
    assert rows[0]["to_username"] == "employee1"
    assert rows[0]["subject"] == "Hello"
    assert rows[0]["created_at"] == "2030-01-01 09:00:00"


def test_recipients_are_the_owner_and_the_attendees(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "employee2")
        add_attendee(db, booking_id, "admin1")
        assert recipients(db, booking_id) == ["admin1", "employee1", "employee2"]


def test_owner_who_is_also_an_attendee_gets_one_email(app):
    booking_id = make_booking(app)
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "employee1")
        assert recipients(db, booking_id) == ["employee1"]


def test_description_has_room_and_times(app):
    booking_id = make_booking(app)
    with app.app_context():
        text = describe_booking(get_db(), booking_id)
    assert "BK-00001" in text
    assert "Alpha (Bengaluru)" in text
    assert "2030-01-15 10:00" in text


def test_confirmation_goes_to_owner_and_attendees(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "employee2")
        assert notify_booking_created(db, booking_id) == 2
    rows = outbox(app)
    assert sorted(row["to_username"] for row in rows) == ["employee1", "employee2"]
    assert all("BK-00001 confirmed" in row["subject"] for row in rows)
    assert "Alpha" in rows[0]["body"]