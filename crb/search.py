from crb.availability import is_room_free
from crb.equipment import has_all_equipment


def find_rooms(db, start, end, location="", min_capacity=1, equipment=None):
    """Return the active rooms that match every filter and are free from start to end."""
    equipment = equipment or []
    rooms = db.execute(
        "SELECT * FROM rooms WHERE active = 1 AND capacity >= ? ORDER BY location, name",
        (min_capacity,),
    ).fetchall()

    results = []
    for room in rooms:
        if location and room["location"].lower() != location.lower():
            continue
        if not has_all_equipment(room["equipment"], equipment):
            continue
        if not is_room_free(db, room["id"], start, end):
            continue
        results.append(room)
    return results


def list_locations(db):
    """The office locations that still have an active room (for the search dropdown)."""
    rows = db.execute(
        "SELECT DISTINCT location FROM rooms WHERE active = 1 ORDER BY location"
    ).fetchall()
    return [row["location"] for row in rows]
