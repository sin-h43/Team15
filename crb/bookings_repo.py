"""Database operations for bookings (US-14 / CRB-F-020)."""

from crb.db import get_db


class BookingConflict(Exception):
    """Raised when a requested slot overlaps an existing confirmed booking."""


class RoomUnavailable(Exception):
    """Raised when the room does not exist, is inactive, or is under maintenance."""


def create_booking(room_id, user_id, start_time, end_time):
    """Save a confirmed booking and return its new ID (CRB-F-020).

    The overlap check and the INSERT run inside one BEGIN IMMEDIATE
    transaction. SQLite lets only one writer hold that lock at a time, so two
    simultaneous requests for the same slot cannot both pass the check: the
    second one waits, then sees the first booking and is rejected.

    Two ranges overlap only when each starts before the other ends, so
    back-to-back bookings are allowed. Cancelled bookings never block.

    Raises RoomUnavailable or BookingConflict; nothing is saved in that case.
    """
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        room = db.execute(
            "SELECT active FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()
        if room is None or not room["active"]:
            raise RoomUnavailable("Room not found or inactive")

        blocked = db.execute(
            """
            SELECT 1 FROM maintenance_blocks
            WHERE room_id = ? AND start_time < ? AND end_time > ?
            """,
            (room_id, end_time, start_time),
        ).fetchone()
        if blocked is not None:
            raise RoomUnavailable("Room is under maintenance at that time")

        clash = db.execute(
            """
            SELECT 1 FROM bookings
            WHERE room_id = ? AND status = 'confirmed'
              AND start_time < ? AND end_time > ?
            """,
            (room_id, end_time, start_time),
        ).fetchone()
        if clash is not None:
            raise BookingConflict("Room is already booked for that time")

        cursor = db.execute(
            """
            INSERT INTO bookings (room_id, user_id, start_time, end_time, status)
            VALUES (?, ?, ?, ?, 'confirmed')
            """,
            (room_id, user_id, start_time, end_time),
        )
        db.commit()
        return cursor.lastrowid
    except Exception:
        db.rollback()
        raise


def get_booking(booking_id):
    """Return a booking as a dictionary, or None if missing."""
    row = get_db().execute(
        "SELECT * FROM bookings WHERE id = ?", (booking_id,)
    ).fetchone()
    return dict(row) if row is not None else None