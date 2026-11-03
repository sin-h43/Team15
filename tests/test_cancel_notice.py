from crb.attendees import add_attendee
from crb.cancel_notice import notify_booking_cancelled
from crb.db import get_db
from tests.helpers import make_booking, make_user, signed_in


def outbox(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM outbox ORDER BY id").fetchall()


def test_every_attendee_and_the_owner_are_told(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "employee2")
        assert notify_booking_cancelled(db, booking_id) == 2
    rows = outbox(app)
    assert sorted(row["to_username"] for row in rows) == ["employee1", "employee2"]
    assert all(row["subject"] == "Booking BK-00001 cancelled" for row in rows)
    assert "cancelled" in rows[0]["body"]


def test_cancelling_through_the_site_sends_the_notice(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        add_attendee(get_db(), booking_id, "employee2")
    client = signed_in(app, "employee1", "emp123")
    assert client.post("/bookings/" + str(booking_id) + "/cancel").status_code == 302
    assert sorted(row["to_username"] for row in outbox(app)) == ["employee1", "employee2"]


def test_admin_cancelling_tells_the_owner(app):
    booking_id = make_booking(app)
    signed_in(app, "admin1", "admin123").post("/bookings/" + str(booking_id) + "/cancel")
    assert [row["to_username"] for row in outbox(app)] == ["employee1"]


def test_second_cancel_sends_nothing_more(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    client.post("/bookings/" + str(booking_id) + "/cancel")
    client.post("/bookings/" + str(booking_id) + "/cancel")
    assert len(outbox(app)) == 1


def test_refused_cancel_sends_nothing(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    signed_in(app, "employee2", "emp234").post("/bookings/" + str(booking_id) + "/cancel")
    assert outbox(app) == []