def is_room_free(db, room_id, start, end):
    """True when no confirmed booking and no maintenance block touches start..end.

    Two time ranges overlap when each one starts before the other ends.
    A booking that ends exactly when another starts does NOT overlap.
    Times are 'YYYY-MM-DD HH:MM' strings, so normal string comparison works.
    """
    booked = db.execute(
        "SELECT 1 FROM bookings "
        "WHERE room_id = ? AND status = 'confirmed' AND start_time < ? AND end_time > ?",
        (room_id, end, start),
    ).fetchone()
    blocked = db.execute(
        "SELECT 1 FROM maintenance_blocks WHERE room_id = ? AND start_time < ? AND end_time > ?",
        (room_id, end, start),
    ).fetchone()
    return booked is None and blocked is None
