from crb.db import get_db
from crb.rooms_repo import search_available_rooms


def test_search_excludes_room_during_maintenance(app):
    with app.app_context():
        db = get_db()
        room_id = db.execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]

        db.execute(
            """
            INSERT INTO maintenance_blocks
                (room_id, start_time, end_time, reason)
            VALUES (?, ?, ?, ?)
            """,
            (
                room_id,
                "2026-11-01 09:00",
                "2026-11-01 11:00",
                "Electrical maintenance",
            ),
        )
        db.commit()

        results = search_available_rooms(
            "2026-11-01 10:00",
            "2026-11-01 10:30",
        )

        assert room_id not in [room["id"] for room in results]


def test_search_includes_room_outside_maintenance(app):
    with app.app_context():
        db = get_db()
        room_id = db.execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]

        db.execute(
            """
            INSERT INTO maintenance_blocks
                (room_id, start_time, end_time, reason)
            VALUES (?, ?, ?, ?)
            """,
            (
                room_id,
                "2026-11-01 09:00",
                "2026-11-01 11:00",
                "Electrical maintenance",
            ),
        )
        db.commit()

        results = search_available_rooms(
            "2026-11-01 11:00",
            "2026-11-01 12:00",
        )

        assert room_id in [room["id"] for room in results]


def test_search_excludes_inactive_rooms(app):
    with app.app_context():
        db = get_db()
        room_id = db.execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]

        db.execute(
            "UPDATE rooms SET active = 0 WHERE id = ?",
            (room_id,),
        )
        db.commit()

        results = search_available_rooms(
            "2026-11-01 09:00",
            "2026-11-01 10:00",
        )

        assert room_id not in [room["id"] for room in results]