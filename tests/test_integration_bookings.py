"""TEMPORARY integration tests for the booking flow (Sprint 1, second half).

They check that search, booking, the booking page, attendees and the admin pages work
together. They are deleted in Sprint 2 (commit "chore(test): remove temporary integration tests").
"""
from crb.db import get_db
from tests.helpers import make_user, signed_in

DAY = {"date": "2030-01-15", "start": "10:00", "end": "11:00"}


def search_names(client):
    page = client.get("/rooms/search", query_string=DAY)
    return page.data


def book(client, room_id=1):
    """Book a room the way a user does. If the site asks for a confirmation step, click it too.

    Returns the response of the first request, so tests can check 302 / 409 / 404.
    """
    response = client.post("/rooms/" + str(room_id) + "/book", data=DAY)
    if response.status_code == 302:
        booking_url = response.headers["Location"]
        if b"Confirm booking" in client.get(booking_url).data:
            client.post(booking_url + "/confirm")
    return response


def test_search_then_book_then_see_the_confirmation(app):
    client = signed_in(app, "employee1", "emp123")
    assert b"Alpha" in search_names(client)
    assert book(client).status_code == 302
    response = client.get("/bookings/1")
    assert response.status_code == 200
    assert b"BK-00001" in response.data
    assert b"Alpha" in response.data
    assert b"confirmed" in response.data


def test_booked_room_disappears_from_search(app):
    client = signed_in(app, "employee1", "emp123")
    book(client)
    assert b"Alpha" not in search_names(client)
    assert b"Beta" in search_names(client)


def test_second_person_cannot_take_the_same_slot(app):
    make_user(app, "employee2", "emp234")
    first = signed_in(app, "employee1", "emp123")
    second = signed_in(app, "employee2", "emp234")
    assert book(first).status_code == 302
    assert book(second).status_code == 409
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1


def test_room_blocked_by_admin_cannot_be_booked(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post("/admin/blocks/new", data={"room_id": "1", "start_time": "2030-01-15T09:00",
                                          "end_time": "2030-01-15T12:00", "reason": "Painting"})
    employee = signed_in(app, "employee1", "emp123")
    assert book(employee).status_code == 409


def test_deactivated_room_cannot_be_booked(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post("/admin/rooms/1/deactivate")
    employee = signed_in(app, "employee1", "emp123")
    assert book(employee).status_code == 404


def test_owner_invites_a_colleague_who_can_then_open_the_booking(app):
    make_user(app, "employee2", "emp234")
    make_user(app, "employee3", "emp345")
    owner = signed_in(app, "employee1", "emp123")
    book(owner)
    owner.post("/bookings/1/attendees", data={"username": "employee2"})
    assert b"employee2@crb.example" in owner.get("/bookings/1/attendees").data
    assert signed_in(app, "employee2", "emp234").get("/bookings/1").status_code == 200
    assert signed_in(app, "employee3", "emp345").get("/bookings/1").status_code == 403


def test_my_bookings_and_admin_view(app):
    owner = signed_in(app, "employee1", "emp123")
    book(owner)
    assert b"BK-00001" in owner.get("/my-bookings").data
    assert signed_in(app, "admin1", "admin123").get("/bookings/1").status_code == 200
    assert signed_in(app, "auditor1", "aud123").get("/bookings/1").status_code == 200


def test_attendee_cannot_manage_attendees(app):
    make_user(app, "employee2", "emp234")
    owner = signed_in(app, "employee1", "emp123")
    book(owner)
    owner.post("/bookings/1/attendees", data={"username": "employee2"})
    guest = signed_in(app, "employee2", "emp234")
    assert guest.post("/bookings/1/attendees", data={"username": "admin1"}).status_code == 403