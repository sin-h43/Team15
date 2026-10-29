from crb.booking_code import booking_code
from crb.notifications import describe_booking, recipients, send_email


def notify_booking_cancelled(db, booking_id):
    """Email the owner and every attendee that the booking was cancelled (CRB-F-062)."""
    subject = "Booking " + booking_code(booking_id) + " cancelled"
    body = "This meeting has been cancelled.\n\n" + describe_booking(db, booking_id)
    names = recipients(db, booking_id)
    for name in names:
        send_email(db, name, subject, body)
    return len(names)
