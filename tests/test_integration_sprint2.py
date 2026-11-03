"""TEMPORARY integration tests for Sprint 2.

They run whole user stories through the site: hold -> attendees -> confirm -> emails, cancel,
reschedule, recurring series, reminders, reports and security. They are deleted in the last
commit of Sprint 2 ("chore(test): remove temporary integration tests").
"""
from datetime import datetime, timedelta

from crb.db import get_db
from tests.helpers import booking_status, make_booking, make_user, signed_in

DAY = {"date": "2030-01-15", "start": "10:00", "end": "11:00"}


def outbox(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM outbox ORDER BY id").fetchall()


def search_page(client, **extra):
    query = dict(DAY)
    query.update(extra)
    return client.get("/rooms/search", query_string=query).data


def book_and_confirm(client, room_id=1):
    response = client.post("/rooms/" + str(room_id) + "/book", data=DAY)
    assert response.status_code == 302
    url = response.headers["Location"]
    assert client.post(url + "/confirm").status_code == 302
    return url


def test_checkout_with_attendee_ends_in_two_emails_visible_to_admin(app):
    make_user(app, "employee2", "emp234")
    client = signed_in(app, "employee1", "emp123")
    url = client.post("/rooms/1/book", data=DAY).headers["Location"]
    assert booking_status(app, 1) == "held"
    client.post(url + "/attendees", data={"username": "employee2"})
    client.post(url + "/confirm")
    assert booking_status(app, 1) == "confirmed"
    assert sorted(row["to_username"] for row in outbox(app)) == ["employee1", "employee2"]
    page = signed_in(app, "admin1", "admin123").get("/outbox")
    assert b"employee2@crb.example" in page.data


def test_abandoned_hold_frees_the_room_for_someone_else(app):
    make_user(app, "employee2", "emp234")
    first = signed_in(app, "employee1", "emp123")
    second = signed_in(app, "employee2", "emp234")
    first.post("/rooms/1/book", data=DAY)
    assert b"Alpha" not in search_page(second)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE bookings SET hold_expires_at = '2000-01-01 00:00:00'")
        db.commit()
    assert b"Alpha" in search_page(second)
    assert second.post("/rooms/1/book", data=DAY).status_code == 302
    assert first.post("/bookings/1/confirm").status_code == 409


def test_cancel_frees_the_room_tells_people_and_admin_cancel_is_audited(app):
    make_user(app, "employee2", "emp234")
    owner = signed_in(app, "employee1", "emp123")
    url = book_and_confirm(owner)
    owner.post(url + "/attendees", data={"username": "employee2"})
    admin = signed_in(app, "admin1", "admin123")
    assert admin.post(url + "/cancel").status_code == 302
    assert booking_status(app, 1) == "cancelled"
    assert b"Alpha" in search_page(owner)
    subjects = [row["subject"] for row in outbox(app)]
    assert subjects.count("Booking BK-00001 cancelled") == 2
    assert b"BOOKING_CANCELLED" in admin.get("/audit").data


def test_rescheduling_moves_the_booking_and_frees_the_old_slot(app):
    owner = signed_in(app, "employee1", "emp123")
    url = book_and_confirm(owner)
    response = owner.post(url + "/reschedule", data={"room_id": "2", "date": "2030-01-15",
                                                     "start": "14:00", "end": "15:00"})
    assert response.status_code == 302
    assert b"Alpha" in search_page(owner)
    assert b"Beta" not in search_page(owner, start="14:00", end="15:00")


def test_recurring_series_with_a_busy_date_then_one_date_cancelled(app):
    # C's recurrence runs from the start date up to 90 days from today, so use dates near today.
    first = (datetime.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    second = first + timedelta(days=7)
    stamp = "%Y-%m-%d %H:%M"
    make_booking(app, user_id=2,
                 start=second.strftime(stamp),
                 end=(second + timedelta(hours=1)).strftime(stamp))
    client = signed_in(app, "employee1", "emp123")
    response = client.post("/recurring", data={
        "room_id": "1",
        "date": first.strftime("%Y-%m-%d"),
        "start": "10:00",
        "end": "11:00",
        "frequency": "weekly",
    })
    assert response.status_code == 200
    with app.app_context():
        rows = get_db().execute(
            "SELECT id, start_time FROM bookings WHERE series_id IS NOT NULL ORDER BY id"
        ).fetchall()
    assert len(rows) >= 2
    assert second.strftime(stamp) not in [row["start_time"] for row in rows]
    assert client.post("/bookings/" + str(rows[0]["id"]) + "/cancel").status_code == 302
    assert booking_status(app, rows[0]["id"]) == "cancelled"
    assert booking_status(app, rows[1]["id"]) == "confirmed"


def test_report_counts_only_confirmed_bookings(app):
    owner = signed_in(app, "employee1", "emp123")
    url = book_and_confirm(owner)
    owner.post("/rooms/2/book", data=DAY)  # still only held
    admin = signed_in(app, "admin1", "admin123")
    query = {"start": "2030-01-01", "end": "2030-01-31"}
    page = admin.get("/reports/utilisation", query_string=query).data.decode()
    assert "<td>Alpha</td>" in page
    owner.post(url + "/cancel")
    after = admin.get("/reports/utilisation", query_string=query).data.decode()
    assert after != page


def test_reminder_job_sends_one_reminder_per_booking(app):
    soon = datetime.now() + timedelta(minutes=5)
    make_booking(app, start=soon.strftime("%Y-%m-%d %H:%M"),
                 end=(soon + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"))
    runner = app.test_cli_runner()
    assert "1 reminder(s) sent." in runner.invoke(args=["send-reminders"]).output
    assert "0 reminder(s) sent." in runner.invoke(args=["send-reminders"]).output
    assert len(outbox(app)) == 1


def test_attendee_details_are_encrypted_in_the_database_but_readable_on_the_page(app):
    make_user(app, "employee2", "emp234")
    owner = signed_in(app, "employee1", "emp123")
    url = book_and_confirm(owner)
    owner.post(url + "/attendees", data={"username": "employee2"})
    with app.app_context():
        raw = get_db().execute("SELECT name, email FROM attendees").fetchone()
    assert "employee2" not in raw["name"] + raw["email"]
    assert b"employee2@crb.example" in owner.get(url + "/attendees").data

def test_old_audit_rows_are_purged_but_new_ones_stay(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post("/admin/blocks/new", data={"room_id": "1", "start_time": "2030-01-15T09:00",
                                          "end_time": "2030-01-15T10:00", "reason": "Cleaning"})
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO audit_log (actor, action, detail, created_at) "
                   "VALUES ('admin1', 'OLD', 'x', '2001-01-01 10:00:00')")
        db.commit()
    assert "1 old audit row(s) removed." in app.test_cli_runner().invoke(args=["purge-old-logs"]).output
    page = admin.get("/audit").data
    assert b"maintenance_block_created" in page
    assert b"OLD" not in page


def test_roles_are_enforced_on_the_new_pages(app):
    owner = signed_in(app, "employee1", "emp123")
    book_and_confirm(owner)
    assert owner.get("/reports/utilisation").status_code == 403
    assert owner.get("/outbox").status_code == 403
    auditor = signed_in(app, "auditor1", "aud123")
    assert auditor.get("/bookings/1").status_code == 200
    assert auditor.post("/bookings/1/cancel").status_code == 403
    assert auditor.get("/bookings/1/attendees").status_code == 403
    assert booking_status(app, 1) == "confirmed"


def test_login_cookie_and_pages_carry_the_security_settings(app):
    response = app.test_client().post("/login", data={"username": "employee1", "password": "emp123"})
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert response.headers["X-Frame-Options"] == "DENY"