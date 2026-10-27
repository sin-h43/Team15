
from crb.booking_service import BookingError, NotAllowed, NotFound, get_booking
from datetime import datetime

from crb.availability import is_room_free
from crb.validators import TIME_FORMAT


def cancel_booking(db, booking_id, user_id, role):
    """Cancel one booking occurrence (CRB-F-031 / CRB-F-041)."""
    booking = get_booking(db, booking_id)
    if booking is None:
        raise NotFound("Booking not found")
    if booking["user_id"] != user_id and role != "admin":
        raise NotAllowed("Only the owner or an admin can cancel this booking")
    if booking["status"] not in ("held", "confirmed"):
        raise BookingError("This booking is already " + booking["status"])

    db.execute(
        "UPDATE bookings SET status = 'cancelled', hold_expires_at = NULL WHERE id = ?",
        (booking_id,),
    )
    db.commit()


def cancel_occurrence(db, booking_id, user_id, role):
    """Cancel only the selected occurrence, never the whole recurring series."""
    booking = get_booking(db, booking_id)
    if booking is None:
        raise NotFound("Booking not found")
    if booking["user_id"] != user_id and role != "admin":
        raise NotAllowed("Only the owner or an admin can cancel this booking")
    if booking["status"] not in ("held", "confirmed"):
        raise BookingError("This booking is already " + booking["status"])

    db.execute(
        "UPDATE bookings SET status = 'cancelled', hold_expires_at = NULL WHERE id = ?",
        (booking_id,),
    )
    db.commit()

def edit_occurrence(db, booking_id, user_id, role, start, end, now=None):
    """Edit one booking occurrence without changing its recurring series."""
    from datetime import datetime

    from crb.availability import is_room_free

    booking = get_booking(db, booking_id)
    if booking is None:
        raise NotFound("Booking not found")
    if booking["user_id"] != user_id and role != "admin":
        raise NotAllowed("Only the owner or an admin can edit this booking")
    if booking["status"] != "confirmed":
        raise BookingError("Only confirmed bookings can be edited")

    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        raise BookingError("Invalid date or time")

    if end_dt <= start_dt:
        raise BookingError("End time must be after start time")

    now = now or datetime.now()
    if start_dt <= now:
        raise BookingError("You cannot book a time in the past")

    db.commit()
    db.execute("BEGIN IMMEDIATE")
    try:
        if not is_room_free(
            db,
            booking["room_id"],
            start,
            end,
            ignore_booking_id=booking_id,
            now=now,
        ):
            raise BookingError("That room is already booked for this time")

        db.execute(
            "UPDATE bookings SET start_time = ?, end_time = ? WHERE id = ?",
            (start, end, booking_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
