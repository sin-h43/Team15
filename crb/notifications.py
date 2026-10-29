from datetime import datetime

from crb.booking_code import booking_code
from crb.booking_service import get_booking


def send_email(db, to_username, subject, body, now=None):
    """Save an email in the outbox table (a real mail server would be plugged in here)."""
    created = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO outbox (to_username, subject, body, created_at) VALUES (?, ?, ?, ?)",
        (to_username, subject, body, created),
    )
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