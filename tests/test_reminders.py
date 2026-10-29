from datetime import datetime, timedelta

from crb.attendees import add_attendee
from crb.db import get_db
from crb.reminders import REMINDER_MINUTES, send_due_reminders
from tests.helpers import make_booking, make_user

NOW = datetime(2030, 1, 15, 9, 51, 30)


def outbox(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM outbox ORDER BY id").fetchall()


def run(app, now=NOW):
    with app.app_context():
        return send_due_reminders(get_db(), now)


def test_reminder_window_is_ten_minutes():
    assert REMINDER_MINUTES == 10


def test_booking_starting_in_nine_minutes_is_reminded(app):
    make_booking(app, start="2030-01-15 10:00", end="2030-01-15 11:00")
    assert run(app) == 1
    rows = outbox(app)
    assert len(rows) == 1
    assert rows[0]["to_username"] == "employee1"
    assert "Reminder: BK-00001 starts at 10:00" == rows[0]["subject"]


def test_booking_later_than_ten_minutes_is_not_reminded(app):
    make_booking(app, start="2030-01-15 10:30", end="2030-01-15 11:00")
    assert run(app) == 0
    assert outbox(app) == []


def test_booking_that_already_started_is_not_reminded(app):
    make_booking(app, start="2030-01-15 09:30", end="2030-01-15 10:30")
    assert run(app) == 0


def test_each_booking_is_reminded_only_once(app):
    make_booking(app, start="2030-01-15 10:00", end="2030-01-15 11:00")
    assert run(app) == 1
    assert run(app) == 0
    assert len(outbox(app)) == 1


def test_attendees_are_reminded_too(app):
    booking_id = make_booking(app, start="2030-01-15 10:00", end="2030-01-15 11:00")
    make_user(app, "employee2", "emp234")
    with app.app_context():
        add_attendee(get_db(), booking_id, "employee2")
    assert run(app) == 1
    assert sorted(row["to_username"] for row in outbox(app)) == ["employee1", "employee2"]


def test_cancelled_and_held_bookings_are_not_reminded(app):
    make_booking(app, start="2030-01-15 10:00", end="2030-01-15 11:00", status="cancelled")
    make_booking(app, room_id=2, start="2030-01-15 10:00", end="2030-01-15 11:00",
                 status="held", hold_expires_at="2030-01-15 09:53:00")
    assert run(app) == 0


def test_command_line_job_reports_how_many_were_sent(app):
    soon = datetime.now() + timedelta(minutes=5)
    make_booking(app, start=soon.strftime("%Y-%m-%d %H:%M"),
                 end=(soon + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"))
    result = app.test_cli_runner().invoke(args=["send-reminders"])
    assert "1 reminder(s) sent." in result.output
    assert len(outbox(app)) == 1