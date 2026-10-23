from datetime import datetime

from crb.availability import is_room_free

TIME_FORMAT = "%Y-%m-%d %H:%M"


class BookingError(Exception):
    """A booking cannot be made. The message is safe to show to the user."""


class NotFound(BookingError):
    """The booking or room does not exist."""


class NotAllowed(BookingError):
    """The user is not allowed to do this to the booking."""


def create_booking(db, user_id, room_id, start, end, now=None,
                   status="confirmed", hold_expires_at=None, series_id=None):
    """Insert a booking if the room exists, is active and is free. Returns the new id.

    The check and the insert run inside ONE transaction (BEGIN IMMEDIATE locks the
    database for writing), so two people cannot book the same slot at the same time.
    """
    now = now or datetime.now()
    if start < now.strftime(TIME_FORMAT):
        raise BookingError("You cannot book a time in the past")
    db.commit()  # make sure no earlier transaction is still open
    db.execute("BEGIN IMMEDIATE")
    try:
        room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None or not room["active"]:
            raise NotFound("That room is not available")
        if not is_room_free(db, room_id, start, end, now=now):
            raise BookingError("That room is already booked for this time")
        cursor = db.execute(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time, status, hold_expires_at, series_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (room_id, user_id, start, end, status, hold_expires_at, series_id),
        )
        db.commit()
        return cursor.lastrowid
    except Exception:
        db.rollback()
        raise


def get_booking(db, booking_id):
    return db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
