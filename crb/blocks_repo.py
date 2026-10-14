
"""Database operations for room maintenance blocks."""

from crb.db import get_db


def create_block(room_id, start_time, end_time, reason):
    """Create a maintenance block and return its new ID."""
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO maintenance_blocks (room_id, start_time, end_time, reason)
        VALUES (?, ?, ?, ?)
        """,
        (room_id, start_time, end_time, reason),
    )
    db.commit()
    return cursor.lastrowid


def get_block(block_id):
    """Return a maintenance block as a dictionary, or None if missing."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM maintenance_blocks WHERE id = ?",
        (block_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def list_blocks(room_id=None):
    """List maintenance blocks, optionally filtered by room ID."""
    db = get_db()

    if room_id is None:
        rows = db.execute(
            "SELECT * FROM maintenance_blocks ORDER BY start_time, id"
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT * FROM maintenance_blocks
            WHERE room_id = ?
            ORDER BY start_time, id
            """,
            (room_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def delete_block(block_id):
    """Delete a maintenance block. Return True if one was deleted."""
    db = get_db()
    cursor = db.execute(
        "DELETE FROM maintenance_blocks WHERE id = ?",
        (block_id,),
    )
    db.commit()
    return cursor.rowcount > 0
