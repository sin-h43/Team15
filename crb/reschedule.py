from datetime import datetime

from crb.availability import is_room_free
from crb.booking_service import TIME_FORMAT, BookingError, NotAllowed, NotFound, get_booking


def reschedule_booking(db, booking_id, user_id, role, room_id, start, end, now=None):
    """Move a confirmed booking to a new time and/or room (CRB-F-030).

    The new slot is checked like a new booking, except that the booking does not clash with
    itself. If the new slot is taken, nothing changes and the old booking stays.
    """
    now = now or datetime.now()
    if start < now.strftime(TIME_FORMAT):
        raise BookingError("You cannot book a time in the past")
    db.commit()  # make sure no earlier transaction is still open
    db.execute("BEGIN IMMEDIATE")
    try:
        booking = get_booking(db, booking_id)
        if booking is None:
            raise NotFound("Booking not found")
        if booking["user_id"] != user_id and role != "admin":
            raise NotAllowed("Only the owner or an admin can move this booking")
        if booking["status"] != "confirmed":
            raise BookingError("Only confirmed bookings can be moved")
        room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None or not room["active"]:
            raise NotFound("That room is not available")
        if not is_room_free(db, room_id, start, end, ignore_booking_id=booking_id, now=now):
            raise BookingError("That room is already booked for this time")
        db.execute(
            "UPDATE bookings SET room_id = ?, start_time = ?, end_time = ?, reminder_sent = 0 WHERE id = ?",
            (room_id, start, end, booking_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise