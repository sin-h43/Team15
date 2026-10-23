def split_equipment(text):
    """'projector,whiteboard' -> ['projector', 'whiteboard'] ('' -> [])."""
    return [item for item in text.split(",") if item]


def has_all_equipment(room_equipment, wanted):
    """True when the room has every wanted item (an empty wish list always passes)."""
    have = split_equipment(room_equipment)
    return all(item in have for item in wanted)
