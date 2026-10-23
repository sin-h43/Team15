def booking_code(booking_id):
    """The booking ID that people see and quote, e.g. 12 -> 'BK-00012' (CRB-F-023)."""
    return "BK-" + str(booking_id).zfill(5)
