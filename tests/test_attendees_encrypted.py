from crb.attendees import add_attendee, list_attendees
from crb.db import get_db
from tests.helpers import make_booking, make_user, signed_in


def raw_rows(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM attendees").fetchall()


def test_name_and_email_are_not_readable_in_the_database(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        add_attendee(get_db(), booking_id, "employee2")
    row = raw_rows(app)[0]
    assert "employee2" not in row["name"]
    assert "employee2" not in row["email"]
    assert "crb.example" not in row["email"]


def test_the_application_still_reads_them_in_plain_text(app):
    booking_id = make_booking(app)
    make_user(app, "employee2", "emp234")
    with app.app_context():
        db = get_db()
        add_attendee(db, booking_id, "employee2")
        people = list_attendees(db, booking_id)
    assert people[0]["name"] == "employee2"
    assert people[0]["email"] == "employee2@crb.example"


def test_attendee_page_shows_plain_text(app):
    booking_id = make_booking(app)
    client = signed_in(app, "employee1", "emp123")
    client.post("/bookings/" + str(booking_id) + "/attendees", data={"username": "admin1"})
    page = client.get("/bookings/" + str(booking_id) + "/attendees")
    assert b"admin1@crb.example" in page.data


def test_user_id_stays_readable_for_lookups(app):
    booking_id = make_booking(app)
    with app.app_context():
        add_attendee(get_db(), booking_id, "admin1")
    assert raw_rows(app)[0]["user_id"] == 2
