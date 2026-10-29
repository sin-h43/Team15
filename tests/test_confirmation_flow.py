from crb.attendees import add_attendee
from crb.db import get_db
from tests.helpers import make_user, signed_in

GOOD = {"date": "2030-01-15", "start": "10:00", "end": "11:00"}


def outbox_names(app):
    with app.app_context():
        rows = get_db().execute("SELECT to_username FROM outbox ORDER BY id").fetchall()
    return [row["to_username"] for row in rows]


def test_holding_a_room_sends_nothing_yet(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    assert outbox_names(app) == []


def test_confirming_sends_the_confirmation_email(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    client.post("/bookings/1/confirm")
    assert outbox_names(app) == ["employee1"]


def test_attendees_added_during_checkout_are_emailed_too(app):
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    client.post("/bookings/1/attendees", data={"username": "employee2"})
    client.post("/bookings/1/confirm")
    assert sorted(outbox_names(app)) == ["employee1", "employee2"]


def test_confirming_twice_sends_only_one_set_of_emails(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    client.post("/bookings/1/confirm")
    client.post("/bookings/1/confirm")
    assert outbox_names(app) == ["employee1"]


def test_failed_confirmation_sends_nothing(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE bookings SET hold_expires_at = '2000-01-01 00:00:00'")
        db.commit()
    assert client.post("/bookings/1/confirm").status_code == 409
    assert outbox_names(app) == []


def test_admin_sees_the_outbox(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    client.post("/bookings/1/confirm")
    page = signed_in(app, "admin1", "admin123").get("/outbox")
    assert page.status_code == 200
    assert b"employee1@crb.example" in page.data
    assert b"BK-00001 confirmed" in page.data


def test_employee_gets_403_on_the_outbox(app):
    assert signed_in(app, "employee1", "emp123").get("/outbox").status_code == 403


def test_visitor_is_sent_to_login_from_the_outbox(client):
    assert client.get("/outbox").status_code == 302


def test_empty_outbox_message(app):
    page = signed_in(app, "admin1", "admin123").get("/outbox")
    assert b"No emails have been sent yet" in page.data