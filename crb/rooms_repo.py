
"""Database operations for conference rooms."""

from crb.db import get_db


def create_room(name, location, capacity, equipment=""):
    """Create a room and return its new ID."""
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO rooms (name, location, capacity, equipment)
        VALUES (?, ?, ?, ?)
        """,
        (name, location, capacity, equipment),
    )
    db.commit()
    return cursor.lastrowid


def update_room(room_id, name, location, capacity, equipment=""):
    """Update a room. Return True if a room was updated."""
    db = get_db()
    cursor = db.execute(
        """
        UPDATE rooms
        SET name = ?, location = ?, capacity = ?, equipment = ?
        WHERE id = ?
        """,
        (name, location, capacity, equipment, room_id),
    )
    db.commit()
    return cursor.rowcount > 0


def deactivate_room(room_id):
    """Deactivate a room without deleting its record."""
    db = get_db()
    cursor = db.execute(
        "UPDATE rooms SET active = 0 WHERE id = ?",
        (room_id,),
    )
    db.commit()
    return cursor.rowcount > 0


def get_room(room_id):
    """Return a room as a dictionary, or None if it doesn't exist."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM rooms WHERE id = ?",
        (room_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def list_rooms(include_inactive=False):
    """Return rooms ordered by ID, excluding inactive rooms by default."""
    db = get_db()

    if include_inactive:
        rows = db.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM rooms WHERE active = 1 ORDER BY id"
        ).fetchall()

    return [dict(row) for row in rows]
def search_available_rooms(start_time, end_time):
    """Return active rooms not blocked during the requested time range."""
    db = get_db()
    rows = db.execute(
        """
        SELECT r.*
        FROM rooms AS r
        WHERE r.active = 1
          AND NOT EXISTS (
              SELECT 1
              FROM maintenance_blocks AS m
              WHERE m.room_id = r.id
                AND m.start_time < ?
                AND m.end_time > ?
          )
        ORDER BY r.id
        """,
        (end_time, start_time),
    ).fetchall()

    return [dict(row) for row in rows]