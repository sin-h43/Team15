from crb.db import get_db
from tests.helpers import make_booking, make_user, signed_in

GOOD = {"date": "2030-01-15", "start": "10:00", "end": "11:00"}


def booking_rows(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM bookings ORDER BY id").fetchall()


def test_visitor_is_sent_to_login(client):
    response = client.post("/rooms/1/book", data=GOOD)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_booking_form_shows_the_room(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.get("/rooms/2/book", query_string=GOOD)
    assert response.status_code == 200
    assert b"Beta" in response.data
    assert b"2030-01-15" in response.data


def test_booking_a_free_room_saves_it_and_redirects(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/rooms/1/book", data=GOOD)
    rows = booking_rows(app)
    assert len(rows) == 1
    assert rows[0]["status"] == "confirmed"
    assert rows[0]["user_id"] == 1
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/bookings/" + str(rows[0]["id"]))


def test_double_booking_is_rejected_with_409(app):
    make_booking(app)
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee2", "emp234")
    response = client.post("/rooms/1/book", data=GOOD)
    assert response.status_code == 409
    assert b"already booked" in response.data
    assert len(booking_rows(app)) == 1


def test_bad_time_range_is_rejected_with_400(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/rooms/1/book", data={"date": "2030-01-15", "start": "11:00", "end": "10:00"})
    assert response.status_code == 400
    assert b"Invalid time range" in response.data
    assert booking_rows(app) == []


def test_time_in_the_past_is_rejected(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/rooms/1/book", data={"date": "2020-01-15", "start": "10:00", "end": "11:00"})
    assert response.status_code == 409
    assert b"past" in response.data


def test_unknown_room_is_404(app):
    client = signed_in(app, "employee1", "emp123")
    assert client.get("/rooms/99/book").status_code == 404
    assert client.post("/rooms/99/book", data=GOOD).status_code == 404


def test_deactivated_room_is_404(app):
    with app.app_context():
        db = get_db()
        db.execute("UPDATE rooms SET active = 0 WHERE id = 1")
        db.commit()
    client = signed_in(app, "employee1", "emp123")
    assert client.get("/rooms/1/book").status_code == 404


def test_search_results_link_to_the_booking_form(app):
    client = signed_in(app, "employee1", "emp123")
    response = client.get("/rooms/search", query_string=GOOD)
    assert b"/rooms/1/book?date=2030-01-15" in response.data