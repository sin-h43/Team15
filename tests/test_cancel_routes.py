from crb.db import get_db
from tests.helpers import booking_status, make_booking, make_user, signed_in


def audit_actions(app):
    with app.app_context():
        rows = get_db().execute("SELECT action FROM audit_log ORDER BY id").fetchall()
    return [row["action"] for row in rows]


def test_visitor_is_sent_to_login(app):
    booking_id = make_booking(app)
    response = app.test_client().post("/bookings/" + str(booking_id) + "/cancel")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_owner_cancels_and_is_sent_back_to_the_booking(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/bookings/" + str(booking_id) + "/cancel")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/bookings/" + str(booking_id))
    assert booking_status(app, booking_id) == "cancelled"


def test_cancelling_via_get_is_not_allowed(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    assert client.get("/bookings/" + str(booking_id) + "/cancel").status_code == 405


def test_stranger_gets_403_and_nothing_changes(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee2", "emp234")
    assert client.post("/bookings/" + str(booking_id) + "/cancel").status_code == 403
    assert booking_status(app, booking_id) == "confirmed"


def test_admin_cancel_is_written_to_the_audit_log(app):
    booking_id = make_booking(app)
    client = signed_in(app, "admin1", "admin123")
    assert client.post("/bookings/" + str(booking_id) + "/cancel").status_code == 302
    assert audit_actions(app) == ["BOOKING_CANCELLED"]


def test_owner_cancel_is_not_an_admin_action(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    client.post("/bookings/" + str(booking_id) + "/cancel")
    assert audit_actions(app) == []


def test_second_cancel_shows_a_conflict_message(app):
    booking_id = make_booking(app, status="cancelled")
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/bookings/" + str(booking_id) + "/cancel")
    assert response.status_code == 409
    assert b"already cancelled" in response.data


def test_unknown_booking_is_404(app):
    client = signed_in(app, "employee1", "emp123")
    assert client.post("/bookings/999/cancel").status_code == 404


def test_booking_page_shows_cancel_button_only_while_active(app):
    active = make_booking(app)
    gone = make_booking(app, room_id=2, status="cancelled")
    client = signed_in(app, "employee1", "emp123")
    assert b"Cancel booking" in client.get("/bookings/" + str(active)).data
    assert b"Cancel booking" not in client.get("/bookings/" + str(gone)).data
