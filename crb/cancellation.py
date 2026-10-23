from crb.booking_service import BookingError, NotAllowed, NotFound, get_booking


def cancel_booking(db, booking_id, user_id, role):
    """Cancel a held or confirmed booking (CRB-F-031). The owner or an admin may do it."""
    booking = get_booking(db, booking_id)
    if booking is None:
        raise NotFound("Booking not found")
    if booking["user_id"] != user_id and role != "admin":
        raise NotAllowed("Only the owner or an admin can cancel this booking")
    if booking["status"] not in ("held", "confirmed"):
        raise BookingError("This booking is already " + booking["status"])
    db.execute(
        "UPDATE bookings SET status = 'cancelled', hold_expires_at = NULL WHERE id = ?", (booking_id,)
    )
    db.commit()
