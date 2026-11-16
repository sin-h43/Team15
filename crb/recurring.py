from datetime import datetime, timedelta

from flask import current_app

from crb.availability import is_room_free
from crb.booking_service import BookingError, NotFound
from crb.clock import local_now

TIME_FORMAT = "%Y-%m-%d %H:%M"


DEFAULT_HORIZON_DAYS = 90


def horizon_days():
    """How far ahead a series may run (CRB-F-040): RECURRING_HORIZON_DAYS, default 90."""
    try:
        return int(current_app.config.get("RECURRING_HORIZON_DAYS") or DEFAULT_HORIZON_DAYS)
    except RuntimeError:  # called outside the app (plain unit tests)
        return DEFAULT_HORIZON_DAYS


def create_recurring_bookings(db, user_id, room_id, start, end, frequency, now=None, until=None,
                              horizon=None):
    """Create daily or weekly occurrences from `start` up to `until` (a 'YYYY-MM-DD' date, inclusive).

    Without `until` the series runs to the end of the horizon. The horizon is configurable
    (default 90 days) and `until` may not go past it.
    """
    if frequency not in ("daily", "weekly"):
        raise BookingError("Choose daily or weekly recurrence")

    now = now or local_now()
    horizon = horizon or horizon_days()
    try:
        start_dt = datetime.strptime(start, TIME_FORMAT)
        end_dt = datetime.strptime(end, TIME_FORMAT)
    except (TypeError, ValueError):
        raise BookingError("Invalid date or time")

    if end_dt <= start_dt:
        raise BookingError("End time must be after start time")
    if start_dt <= now:
        raise BookingError("You cannot book a time in the past")
    last_allowed = now + timedelta(days=horizon)
    if start_dt > last_allowed:
        raise BookingError("Bookings must start within the next " + str(horizon) + " days")

    if until:
        try:
            until_date = datetime.strptime(until, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise BookingError("Invalid end date")
        if until_date < start_dt.date():
            raise BookingError("The end date must not be before the first date")
        if until_date > last_allowed.date():
            raise BookingError("The end date must be within the next " + str(horizon) + " days")
    else:
        until_date = last_allowed.date()

    room = db.execute(
        "SELECT * FROM rooms WHERE id = ?", (room_id,)
    ).fetchone()
    if room is None or not room["active"]:
        raise NotFound("That room is not available")

    step = timedelta(days=1 if frequency == "daily" else 7)
    occurrences = []
    conflicts = []
    current_start, current_end = start_dt, end_dt

    while current_start <= last_allowed and current_start.date() <= until_date:
        occurrences.append((
            current_start.strftime(TIME_FORMAT),
            current_end.strftime(TIME_FORMAT),
        ))
        current_start += step
        current_end += step

    db.begin_write()
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