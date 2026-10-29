from crb.db import get_db
from tests.helpers import make_booking, make_user, signed_in

NEW = {"room_id": "2", "date": "2030-01-16", "start": "14:00", "end": "15:00"}


def row(app, booking_id):
    with app.app_context():
        return get_db().execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()


def test_visitor_is_sent_to_login(app):
    booking_id = make_booking(app)
    assert app.test_client().get("/bookings/" + str(booking_id) + "/reschedule").status_code == 302


def test_form_is_filled_with_the_current_time(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    response = client.get("/bookings/" + str(booking_id) + "/reschedule")
    assert response.status_code == 200
    assert b'value="2030-01-15"' in response.data
    assert b'value="10:00"' in response.data


def test_owner_moves_the_booking(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/bookings/" + str(booking_id) + "/reschedule", data=NEW)
    assert response.status_code == 302
    moved = row(app, booking_id)
    assert moved["room_id"] == 2
    assert moved["start_time"] == "2030-01-16 14:00"


def test_taken_slot_shows_a_conflict_and_changes_nothing(app):
    booking_id = make_booking(app)
    make_booking(app, room_id=2, user_id=2, start="2030-01-16 14:30", end="2030-01-16 15:30")
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/bookings/" + str(booking_id) + "/reschedule", data=NEW)
    assert response.status_code == 409
    assert b"already booked" in response.data
    assert row(app, booking_id)["room_id"] == 1


def test_bad_input_is_a_400(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    bad = dict(NEW, start="16:00", end="15:00")
    assert client.post("/bookings/" + str(booking_id) + "/reschedule", data=bad).status_code == 400
    assert client.post("/bookings/" + str(booking_id) + "/reschedule", data=dict(NEW, room_id="x")).status_code == 400


def test_stranger_gets_403(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee2", "emp234")
    assert client.get("/bookings/" + str(booking_id) + "/reschedule").status_code == 403
    assert client.post("/bookings/" + str(booking_id) + "/reschedule", data=NEW).status_code == 403
    assert row(app, booking_id)["room_id"] == 1


def test_unknown_booking_is_404(app):
    client = signed_in(app, "employee1", "emp123")
    assert client.get("/bookings/999/reschedule").status_code == 404


def test_booking_page_links_to_the_move_form_only_when_confirmed(app):
    active = make_booking(app)
    held = make_booking(app, room_id=2, status="held", hold_expires_at="2030-01-15 09:02:00")
    client = signed_in(app, "employee1", "emp123")
    assert b"Move to another time" in client.get("/bookings/" + str(active)).data
    assert b"Move to another time" not in client.get("/bookings/" + str(held)).data