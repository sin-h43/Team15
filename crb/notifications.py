from datetime import datetime

from flask import current_app

from crb.booking_code import booking_code
from crb.booking_service import get_booking
from crb.mailer import MailError, can_deliver_to, deliver, mail_enabled
from crb.clock import local_now


def send_email(db, to_username, subject, body, now=None):
    """Save an email in the outbox table and, when a mail service is configured, send it.

    A failed send never breaks the booking: it is recorded as 'failed' and logged.
    """
    created = (now or local_now()).strftime("%Y-%m-%d %H:%M:%S")
    cursor = db.execute(
        "INSERT INTO outbox (to_username, subject, body, created_at) VALUES (?, ?, ?, ?)",
        (to_username, subject, body, created),
    )
    db.commit()
    if not mail_enabled():
        return
    from crb.attendees import email_for  # imported here: attendees imports booking code too

    address = email_for(to_username, db)
    if not can_deliver_to(address):
        return
    try:
        deliver(address, subject, body)
        status = "sent"
    except MailError as problem:
        current_app.logger.warning("email to %s failed: %s", to_username, problem)
        status = "failed"
    db.execute("UPDATE outbox SET status = ? WHERE id = ?", (status, cursor.lastrowid))
    db.commit()


def recipients(db, booking_id):
    """Usernames of the booking owner and all attendees, without duplicates."""
    rows = db.execute(
        "SELECT u.username FROM users u WHERE u.id = (SELECT user_id FROM bookings WHERE id = ?) "
        "UNION "
        "SELECT u.username FROM attendees a JOIN users u ON u.id = a.user_id WHERE a.booking_id = ? "
        "ORDER BY 1",
        (booking_id, booking_id),
    ).fetchall()
    return [row["username"] for row in rows]


def describe_booking(db, booking_id):
    """The booking details used in every email."""
    booking = get_booking(db, booking_id)
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (booking["room_id"],)).fetchone()
    return (
        "Booking: " + booking_code(booking_id) + "\n"
        "Room: " + room["name"] + " (" + room["location"] + ")\n"
        "From: " + booking["start_time"] + "\n"
        "To: " + booking["end_time"]
    )


def notify_booking_created(db, booking_id):
    """Email the owner and every attendee that the booking is confirmed (CRB-F-060)."""
    subject = "Booking " + booking_code(booking_id) + " confirmed"
    body = "Your meeting is confirmed.\n\n" + describe_booking(db, booking_id)
    names = recipients(db, booking_id)
    for name in names:
        send_email(db, name, subject, body)
    return len(names)

def notify_booking_changed(db, booking_id):
    """Email the owner and every attendee that the booking was moved (CRB-F-030)."""
    subject = "Booking " + booking_code(booking_id) + " changed"
    body = "Your meeting has been changed.\n\n" + describe_booking(db, booking_id)
    names = recipients(db, booking_id)
    for name in names:
        send_email(db, name, subject, body)
    return len(names)
