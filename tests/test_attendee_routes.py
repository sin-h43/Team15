from crb.attendees import list_attendees
from crb.db import get_db
from tests.helpers import make_booking, make_user, signed_in


def attendees(app, booking_id):
    with app.app_context():
        return list_attendees(get_db(), booking_id)


def test_visitor_is_sent_to_login(app):
    booking_id = make_booking(app)
    response = app.test_client().get("/bookings/" + str(booking_id) + "/attendees")
    assert response.status_code == 302


def test_owner_sees_the_attendee_page(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    response = client.get("/bookings/" + str(booking_id) + "/attendees")
    assert response.status_code == 200
    assert b"No attendees yet" in response.data


def test_owner_adds_an_attendee(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/bookings/" + str(booking_id) + "/attendees", data={"username": "employee2"})
    assert response.status_code == 302
    assert [a["name"] for a in attendees(app, booking_id)] == ["employee2"]
    page = client.get("/bookings/" + str(booking_id) + "/attendees")
    assert b"employee2@crb.example" in page.data


def test_unknown_username_shows_an_error(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/bookings/" + str(booking_id) + "/attendees", data={"username": "nobody"})
    assert response.status_code == 400
    assert b"Unknown employee" in response.data


def test_empty_username_shows_an_error(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/bookings/" + str(booking_id) + "/attendees", data={"username": " "})
    assert response.status_code == 400
    assert b"required" in response.data


def test_someone_else_gets_403(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee2", "emp234")
    assert client.get("/bookings/" + str(booking_id) + "/attendees").status_code == 403
    assert client.post("/bookings/" + str(booking_id) + "/attendees", data={"username": "admin1"}).status_code == 403
    assert attendees(app, booking_id) == []


def test_admin_can_add_attendees_to_any_booking(app):
    booking_id = make_booking(app)
    client = signed_in(app, "admin1", "admin123")
    response = client.post("/bookings/" + str(booking_id) + "/attendees", data={"username": "auditor1"})
    assert response.status_code == 302


def test_unknown_booking_is_404(app):
    client = signed_in(app, "employee1", "emp123")
    assert client.get("/bookings/999/attendees").status_code == 404


def test_booking_page_links_to_the_attendee_page_for_the_owner(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    assert b"Manage attendees" in client.get("/bookings/" + str(booking_id)).data