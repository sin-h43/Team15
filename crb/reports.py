from datetime import datetime, timedelta

from crb.validators import ValidationError


def read_day(text, name):
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValidationError(name + " is not a valid date")


def utilisation(db, start_date, end_date):
    """Confirmed bookings and booked hours per room, for bookings that start from
    start_date up to and including end_date (CRB-F-070). Rooms with no bookings show 0."""
    first = read_day(start_date, "From date")
    last = read_day(end_date, "To date")
    if last < first:
        raise ValidationError("The To date must not be before the From date")
    lower = first.strftime("%Y-%m-%d") + " 00:00"
    upper = (last + timedelta(days=1)).strftime("%Y-%m-%d") + " 00:00"
    rows = db.execute(
        "SELECT r.id, r.name, r.location, COUNT(b.id) AS bookings, "
        "COALESCE(SUM((julianday(b.end_time) - julianday(b.start_time)) * 24), 0) AS hours "
        "FROM rooms r LEFT JOIN bookings b "
        "ON b.room_id = r.id AND b.status = 'confirmed' AND b.start_time >= ? AND b.start_time < ? "
        "GROUP BY r.id ORDER BY r.location, r.name",
        (lower, upper),
    ).fetchall()
    return [
        {"room": row["name"], "location": row["location"],
         "bookings": row["bookings"], "hours": round(row["hours"], 1)}
        for row in rows
    ]