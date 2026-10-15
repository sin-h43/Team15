"""Equipment filter helper for CRB-F-011."""


def room_equipment(room):
    """Return the set of equipment a room has, from its comma-separated text.

    Whitespace and letter case are ignored, so "Projector, Whiteboard" and
    "projector,whiteboard" give the same result.
    """
    return {
        item.strip().casefold()
        for item in (room.get("equipment") or "").split(",")
        if item.strip()
    }


def filter_by_equipment(rooms, required):
    """Keep only rooms that have every item in `required`.

    A room that lacks any required item is excluded. An empty `required`
    list means no filtering, so every room is kept.
    """
    needed = {item.strip().casefold() for item in required if item.strip()}
    return [room for room in rooms if needed <= room_equipment(room)]