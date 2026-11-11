from crb.booking_service import BookingError, NotFound, get_booking
from crb.crypto import decrypt_text, encrypt_text


class AttendeeError(BookingError):
    """The attendee cannot be added. The message is safe to show to the user."""


def email_for(username, db=None):
    """Email address of an employee: the one on their account, else a company-style default."""
    if db is not None:
        row = db.execute("SELECT email FROM users WHERE username = ?", (username,)).fetchone()
        if row is not None and row["email"]:
            return row["email"]
    return username + "@crb.example"


def add_attendee(db, booking_id, username):
    """Invite one internal employee by username or email (CRB-F-022). Returns the new attendee's user id.

    The attendee's name and email are stored encrypted (CRB-SR-006).
    """
    booking = get_booking(db, booking_id)
    if booking is None:
        raise NotFound("Booking not found")
    if booking["status"] not in ("held", "confirmed"):
        raise AttendeeError("Attendees can only be added to an active booking")
    user = db.execute(
        "SELECT * FROM users WHERE (username = ? OR email = ?) AND email_verified = 1",
        (username, username.lower()),
    ).fetchone()
    if user is None:
        raise AttendeeError("Unknown employee: " + username)
    already = db.execute(
        "SELECT 1 FROM attendees WHERE booking_id = ? AND user_id = ?", (booking_id, user["id"])
    ).fetchone()
    if already is not None:
        raise AttendeeError(username + " is already an attendee")
    db.execute(
        "INSERT INTO attendees (booking_id, user_id, name, email) VALUES (?, ?, ?, ?)",
        (booking_id, user["id"], encrypt_text(user["username"]), encrypt_text(email_for(user["username"], db))),
    )
    db.commit()
    return user["id"]


def list_attendees(db, booking_id):
    """Everybody invited to a booking, as plain dictionaries (decrypted)."""
    rows = db.execute(
        "SELECT user_id, name, email FROM attendees WHERE booking_id = ? ORDER BY id", (booking_id,)
    ).fetchall()
    return [
        {"user_id": row["user_id"], "name": decrypt_text(row["name"]), "email": decrypt_text(row["email"])}
        for row in rows
    ]