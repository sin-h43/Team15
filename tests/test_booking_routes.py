from crb.db import get_db
from tests.helpers import booking_status, make_booking, make_user, signed_in

GOOD = {"date": "2030-01-15", "start": "10:00", "end": "11:00"}


def booking_rows(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM bookings ORDER BY id").fetchall()


def test_visitor_is_sent_to_login(client):
    response = client.post("/rooms/1/book", data=GOOD)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_booking_form_explains_the_hold(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.get("/rooms/2/book", query_string=GOOD)
    assert response.status_code == 200
    assert b"Beta" in response.data
    assert b"2 minutes" in response.data


def test_book_places_a_hold_and_redirects(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/rooms/1/book", data=GOOD)
    rows = booking_rows(app)
    assert len(rows) == 1
    assert rows[0]["status"] == "held"
    assert rows[0]["hold_expires_at"] is not None
    assert response.headers["Location"].endswith("/bookings/" + str(rows[0]["id"]))


def test_booking_page_offers_confirm_while_held(app):
    client = signed_in(app, "employee1", "emp123")
    page = client.post("/rooms/1/book", data=GOOD, follow_redirects=True)
    assert b"Confirm booking" in page.data


def test_confirm_makes_the_booking_confirmed(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    response = client.post("/bookings/1/confirm")
    assert response.status_code == 302
    assert booking_status(app, 1) == "confirmed"
    page = client.get("/bookings/1")
    assert b"Confirm booking" not in page.data


def test_confirm_after_the_hold_ran_out_shows_a_message(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE bookings SET hold_expires_at = '2000-01-01 00:00:00'")
        db.commit()
    response = client.post("/bookings/1/confirm")
    assert response.status_code == 409
    assert b"hold has run out" in response.data
    assert booking_status(app, 1) == "expired"


def test_someone_else_cannot_confirm_my_hold(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    make_user(app, "employee2", "emp234")
    other = signed_in(app, "employee2", "emp234")
    assert other.post("/bookings/1/confirm").status_code == 404
    assert booking_status(app, 1) == "held"


def test_held_room_is_not_offered_to_others_in_search(app):
    client = signed_in(app, "employee1", "emp123")
    client.post("/rooms/1/book", data=GOOD)
    make_user(app, "employee2", "emp234")
    other = signed_in(app, "employee2", "emp234")
    page = other.get("/rooms/search", query_string=GOOD)
    assert b"Alpha" not in page.data
    assert b"Beta" in page.data


def test_second_person_cannot_hold_the_same_slot(app):
    make_booking(app)
    make_user(app, "employee2", "emp234")
    other = signed_in(app, "employee2", "emp234")
    response = other.post("/rooms/1/book", data=GOOD)
    assert response.status_code == 409
    assert b"already booked" in response.data


def test_bad_time_range_is_rejected_with_400(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/rooms/1/book", data={"date": "2030-01-15", "start": "11:00", "end": "10:00"})
    assert response.status_code == 400
    assert booking_rows(app) == []


def test_unknown_room_is_404(app):
    client = signed_in(app, "employee1", "emp123")
    assert client.post("/rooms/99/book", data=GOOD).status_code == 404


def test_search_results_still_link_to_the_booking_form(app):
    client = signed_in(app, "employee1", "emp123")
    assert b"/rooms/1/book?date=2030-01-15" in client.get("/rooms/search", query_string=GOOD).data