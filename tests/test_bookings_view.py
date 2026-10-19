from crb.booking_code import booking_code
from crb.db import get_db
from tests.helpers import make_booking, make_user, signed_in


def test_booking_code_is_padded():
    assert booking_code(1) == "BK-00001"
    assert booking_code(123) == "BK-00123"


def test_booking_codes_are_unique(app):
    first = make_booking(app)
    second = make_booking(app, room_id=2)
    assert booking_code(first) != booking_code(second)


def test_visitor_is_sent_to_login(app):
    booking_id = make_booking(app)
    response = app.test_client().get("/bookings/" + str(booking_id))
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_owner_sees_the_confirmation(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    response = client.get("/bookings/" + str(booking_id))
    assert response.status_code == 200
    assert b"BK-00001" in response.data
    assert b"Alpha" in response.data
    assert b"confirmed" in response.data
    assert b"2030-01-15 10:00" in response.data


def test_other_employee_gets_403(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee2", "emp234")
    assert client.get("/bookings/" + str(booking_id)).status_code == 403


def test_admin_and_auditor_can_view_any_booking(app):
    booking_id = make_booking(app)
    for username, password in [("admin1", "admin123"), ("auditor1", "aud123")]:
        client = signed_in(app, username, password)
        assert client.get("/bookings/" + str(booking_id)).status_code == 200


def test_invited_attendee_can_view(app):
    booking_id = make_booking(app)
    other = make_user(app, "employee2", "emp234")
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO attendees (booking_id, user_id, name, email) VALUES (?, ?, 'employee2', 'x')",
            (booking_id, other),
        )
        db.commit()
    client = signed_in(app, "employee2", "emp234")
    assert client.get("/bookings/" + str(booking_id)).status_code == 200


def test_unknown_booking_is_404(app):
    client = signed_in(app, "employee1", "emp123")
    assert client.get("/bookings/999").status_code == 404


def test_my_bookings_lists_only_my_own(app):
    make_booking(app)
    other = make_user(app, "employee2", "emp234")
    make_booking(app, room_id=2, user_id=other)
    client = signed_in(app, "employee1", "emp123")
    response = client.get("/my-bookings")
    assert response.status_code == 200
    assert b"BK-00001" in response.data
    assert b"BK-00002" not in response.data


def test_my_bookings_is_empty_at_first(app):
    client = signed_in(app, "employee1", "emp123")
    assert b"no bookings yet" in client.get("/my-bookings").data


def test_menu_shows_my_bookings_link_after_login(app):
    client = signed_in(app, "employee1", "emp123")
    assert b"My bookings" in client.get("/").data
