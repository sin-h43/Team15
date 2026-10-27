from datetime import datetime, timedelta

from crb.availability import is_room_free
from crb.booking_service import BookingError, NotFound

TIME_FORMAT = "%Y-%m-%d %H:%M"


def create_recurring_bookings(db, user_id, room_id, start, end, frequency, now=None):
    """Create daily or weekly occurrences within the next 90 days."""
    if frequency not in ("daily", "weekly"):
        raise BookingError("Choose daily or weekly recurrence")

    now = now or datetime.now()
    try:
        start_dt = datetime.strptime(start, TIME_FORMAT)
        end_dt = datetime.strptime(end, TIME_FORMAT)
    except (TypeError, ValueError):
        raise BookingError("Invalid date or time")

    if end_dt <= start_dt:
        raise BookingError("End time must be after start time")
    if start_dt <= now:
        raise BookingError("You cannot book a time in the past")
    if start_dt > now + timedelta(days=90):
        raise BookingError("Bookings must start within the next 90 days")

    room = db.execute(
        "SELECT * FROM rooms WHERE id = ?", (room_id,)
    ).fetchone()
    if room is None or not room["active"]:
        raise NotFound("That room is not available")

    step = timedelta(days=1 if frequency == "daily" else 7)
    last_allowed = now + timedelta(days=90)
    occurrences = []
    conflicts = []
    current_start, current_end = start_dt, end_dt

    while current_start <= last_allowed:
        occurrences.append((
            current_start.strftime(TIME_FORMAT),
            current_end.strftime(TIME_FORMAT),
        ))
        current_start += step
        current_end += step

    db.commit()
    db.execute("BEGIN IMMEDIATE")
    try:
        # Allocate a series ID while holding the write transaction.
        series_id = db.execute(
            "SELECT COALESCE(MAX(series_id), 0) + 1 FROM bookings"
        ).fetchone()[0]

        created_ids = []
        for occurrence_start, occurrence_end in occurrences:
            if is_room_free(
                db, room_id, occurrence_start, occurrence_end, now=now
            ):
                cursor = db.execute(
                    "INSERT INTO bookings "
                    "(room_id, user_id, start_time, end_time, status, series_id) "
                    "VALUES (?, ?, ?, ?, 'confirmed', ?)",
                    (room_id, user_id, occurrence_start, occurrence_end, series_id),
                )
                created_ids.append(cursor.lastrowid)
            else:
                conflicts.append(occurrence_start)

        db.commit()
        return {
            "series_id": series_id,
            "booking_ids": created_ids,
            "conflicts": conflicts,
        }
    except Exception:
        db.rollback()
        raise