from datetime import datetime, timedelta

from flask import Blueprint

from crb.booking_code import booking_code
from crb.booking_service import TIME_FORMAT
from crb.db import get_db
from crb.notifications import describe_booking, recipients, send_email

REMINDER_MINUTES = 10

bp = Blueprint("reminders", __name__, cli_group=None)


def send_due_reminders(db, now=None):
    """Email owner and attendees of every confirmed booking that starts within REMINDER_MINUTES.

    Each booking is reminded only once. Returns how many bookings were reminded (CRB-F-061).
    """
    now = now or datetime.now()
    current = now.strftime(TIME_FORMAT)
    soon = (now + timedelta(minutes=REMINDER_MINUTES)).strftime(TIME_FORMAT)
    due = db.execute(
        "SELECT id, start_time FROM bookings "
        "WHERE status = 'confirmed' AND reminder_sent = 0 AND start_time > ? AND start_time <= ?",
        (current, soon),
    ).fetchall()
    for booking in due:
        subject = "Reminder: " + booking_code(booking["id"]) + " starts at " + booking["start_time"][11:16]
        body = "Your meeting starts soon.\n\n" + describe_booking(db, booking["id"])
        for name in recipients(db, booking["id"]):
            send_email(db, name, subject, body, now=now)
        db.execute("UPDATE bookings SET reminder_sent = 1 WHERE id = ?", (booking["id"],))
        db.commit()
    return len(due)


@bp.cli.command("send-reminders")
def send_reminders_command():
    """Send the 10-minute reminders. Run it every minute (cron) or by hand for a demo."""
    count = send_due_reminders(get_db())
    print(str(count) + " reminder(s) sent.")