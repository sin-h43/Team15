from crb.db import get_db
from crb.search import find_rooms, list_locations

START = "2030-01-15 10:00"
END = "2030-01-15 11:00"


def names(rooms):
    return [room["name"] for room in rooms]


def test_no_filters_returns_every_free_room(app):
    with app.app_context():
        assert names(find_rooms(get_db(), START, END)) == ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]


def test_capacity_filter_keeps_big_enough_rooms(app):
    with app.app_context():
        assert names(find_rooms(get_db(), START, END, min_capacity=8)) == ["Beta", "Gamma", "Epsilon"]


def test_location_filter(app):
    with app.app_context():
        assert names(find_rooms(get_db(), START, END, location="Pune")) == ["Delta", "Epsilon"]


def test_location_filter_ignores_letter_case(app):
    with app.app_context():
        assert names(find_rooms(get_db(), START, END, location="pune")) == ["Delta", "Epsilon"]


def test_equipment_filter_needs_every_item(app):
    with app.app_context():
        found = find_rooms(get_db(), START, END, equipment=["projector", "whiteboard"])
        assert names(found) == ["Beta", "Gamma"]


def test_booked_room_is_left_out(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time) VALUES (2, 1, ?, ?)",
            ("2030-01-15 10:30", "2030-01-15 11:30"),
        )
        db.commit()
        assert "Beta" not in names(find_rooms(db, START, END))


def test_blocked_room_is_left_out(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO maintenance_blocks (room_id, start_time, end_time, reason) VALUES (3, ?, ?, 'repair')",
            ("2030-01-15 09:00", "2030-01-15 12:00"),
        )
        db.commit()
        assert "Gamma" not in names(find_rooms(db, START, END))


def test_deactivated_room_is_left_out(app):
    with app.app_context():
        db = get_db()
        db.execute("UPDATE rooms SET active = 0 WHERE name = 'Alpha'")
        db.commit()
        assert "Alpha" not in names(find_rooms(db, START, END))


def test_filters_work_together(app):
    with app.app_context():
        found = find_rooms(get_db(), START, END, location="Bengaluru", min_capacity=10, equipment=["video_conf"])
        assert names(found) == ["Gamma"]


def test_list_locations_returns_each_location_once(app):
    with app.app_context():
        assert list_locations(get_db()) == ["Bengaluru", "Pune"]
