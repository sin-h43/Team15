from datetime import datetime, timedelta

from crb.booking_service import BookingError, NotFound, create_booking, get_booking

HOLD_MINUTES = 2
STAMP = "%Y-%m-%d %H:%M:%S"


def place_hold(db, user_id, room_id, start, end, now=None):
    """Hold a free room for HOLD_MINUTES while the user checks out (CRB-F-021). Returns the booking id."""
    now = now or datetime.now()
    expires = (now + timedelta(minutes=HOLD_MINUTES)).strftime(STAMP)
    return create_booking(
        db, user_id, room_id, start, end, now=now, status="held", hold_expires_at=expires
    )


def confirm_hold(db, booking_id, user_id, now=None):
    """Turn the user's own hold into a confirmed booking.

    Returns True when it was confirmed just now and False when it was already confirmed.
    """
    now = now or datetime.now()
    booking = get_booking(db, booking_id)
    if booking is None or booking["user_id"] != user_id:
        raise NotFound("Booking not found")
    if booking["status"] == "confirmed":
        return False
    if booking["status"] != "held":
        raise BookingError("This booking can no longer be confirmed")
    if booking["hold_expires_at"] <= now.strftime(STAMP):
        db.execute("UPDATE bookings SET status = 'expired' WHERE id = ?", (booking_id,))
        db.commit()
        raise BookingError("Your " + str(HOLD_MINUTES) + "-minute hold has run out. Please search again.")
    db.execute(
        "UPDATE bookings SET status = 'confirmed', hold_expires_at = NULL WHERE id = ?", (booking_id,)
    )
    db.commit()
    return True