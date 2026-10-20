from datetime import datetime


def is_room_free(db, room_id, start, end, ignore_booking_id=None, now=None):
    """True when nothing blocks the room between start and end.

    Blocked means one of:
      - a confirmed booking overlaps,
      - a held booking overlaps and its 2-minute hold has not run out yet,
      - a maintenance block overlaps.
    `ignore_booking_id` lets a booking be moved without clashing with itself.
    Two time ranges overlap when each one starts before the other ends, so a
    booking that ends exactly when another starts does NOT overlap.
    Times are 'YYYY-MM-DD HH:MM' strings, so normal string comparison works.
    """
    now_text = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    booked = db.execute(
        "SELECT 1 FROM bookings "
        "WHERE room_id = ? AND id != ? AND start_time < ? AND end_time > ? "
        "AND (status = 'confirmed' OR (status = 'held' AND hold_expires_at > ?))",
        (room_id, ignore_booking_id or 0, end, start, now_text),
    ).fetchone()
    blocked = db.execute(
        "SELECT 1 FROM maintenance_blocks WHERE room_id = ? AND start_time < ? AND end_time > ?",
        (room_id, end, start),
    ).fetchone()
    return booked is None and blocked is None
