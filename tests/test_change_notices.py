"""Edit/reschedule notify people; admin edits are audited; holds send no cancel notice."""
from crb.db import get_db
from tests.helpers import make_booking, signed_in


def rows(app, sql):
    with app.app_context():
        return get_db().execute(sql).fetchall()


def test_edit_sends_change_notice(app):
    booking_id = make_booking(app, start="2031-01-15 10:00", end="2031-01-15 11:00")
    client = signed_in(app, "employee1", "emp123")
    response = client.post(
        f"/bookings/{booking_id}/edit", data={"date": "2031-01-15", "start": "12:00", "end": "13:00"}
    )
    assert response.status_code == 302
    assert len(rows(app, "SELECT * FROM outbox WHERE subject LIKE '%changed%'")) == 1


def test_admin_reschedule_is_audited_and_notified(app):
    booking_id = make_booking(app, start="2031-01-15 10:00", end="2031-01-15 11:00")
    client = signed_in(app, "admin1", "admin123")
    response = client.post(
        f"/bookings/{booking_id}/reschedule",
        data={"room_id": "2", "date": "2031-01-15", "start": "10:00", "end": "11:00"},
    )
    assert response.status_code == 302
    audit = rows(app, "SELECT actor, action FROM audit_log")
    assert [(r["actor"], r["action"]) for r in audit] == [("admin1", "BOOKING_RESCHEDULED")]
    assert len(rows(app, "SELECT * FROM outbox")) == 1


def test_cancelling_a_hold_sends_no_notice(app):
    booking_id = make_booking(
        app, status="held", start="2031-01-15 10:00", end="2031-01-15 11:00",
        hold_expires_at="2099-01-01 00:00:00",
    )
    client = signed_in(app, "employee1", "emp123")
    assert client.post(f"/bookings/{booking_id}/cancel").status_code == 302
    assert rows(app, "SELECT * FROM outbox") == []


def test_csrf_blocks_posts_without_token_when_enabled(app):
    app.config["CSRF_ENABLED"] = True
    client = app.test_client()
    assert client.post("/login", data={"username": "employee1", "password": "emp123"}).status_code == 400
    page = client.get("/login").data.decode()
    token = page.split('name="csrf_token" value="')[1].split('"')[0]
    ok = client.post("/login", data={"username": "employee1", "password": "emp123", "csrf_token": token})
    assert ok.status_code == 302


def test_admin_room_rejects_unknown_equipment(app):
    client = signed_in(app, "admin1", "admin123")
    response = client.post(
        "/admin/rooms/new",
        data={"name": "X", "location": "Pune", "capacity": "4", "equipment": "laser"},
    )
    assert response.status_code == 400


def test_my_bookings_lists_invited_meetings(app):
    booking_id = make_booking(app, user_id=2, start="2031-01-15 10:00", end="2031-01-15 11:00")
    from crb.attendees import add_attendee
    with app.app_context():
        add_attendee(get_db(), booking_id, "employee1")
    page = signed_in(app, "employee1", "emp123").get("/my-bookings").data.decode()
    assert "BK-%05d" % booking_id in page
