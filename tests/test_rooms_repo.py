
from crb.rooms_repo import (
    create_room,
    deactivate_room,
    get_room,
    list_rooms,
    update_room,
)


def test_create_room(app):
    with app.app_context():
        room_id = create_room("Meeting Room A", "Floor 1", 10, "Projector")
        room = get_room(room_id)

        assert room["name"] == "Meeting Room A"
        assert room["location"] == "Floor 1"
        assert room["capacity"] == 10
        assert room["equipment"] == "Projector"
        assert room["active"] == 1


def test_update_room(app):
    with app.app_context():
        room_id = create_room("Old Room", "Floor 1", 5)
        updated = update_room(room_id, "New Room", "Floor 2", 12, "Whiteboard")

        room = get_room(room_id)

        assert updated is True
        assert room["name"] == "New Room"
        assert room["location"] == "Floor 2"
        assert room["capacity"] == 12
        assert room["equipment"] == "Whiteboard"


def test_deactivate_room(app):
    with app.app_context():
        room_id = create_room("Room B", "Floor 2", 8)

        assert deactivate_room(room_id) is True
        assert get_room(room_id)["active"] == 0


def test_get_room_missing(app):
    with app.app_context():
        assert get_room(99999) is None


def test_list_rooms_excludes_inactive(app):
    with app.app_context():
        room_id = create_room("Temporary Room", "Floor 3", 6)
        deactivate_room(room_id)

        rooms = list_rooms()

        assert all(room["id"] != room_id for room in rooms)


def test_list_rooms_includes_inactive_when_requested(app):
    with app.app_context():
        room_id = create_room("Temporary Room", "Floor 3", 6)
        deactivate_room(room_id)

        rooms = list_rooms(include_inactive=True)

        assert any(
            room["id"] == room_id and room["active"] == 0
            for room in rooms
        )


def test_update_missing_room(app):
    with app.app_context():
        assert update_room(99999, "Missing", "Floor 1", 5) is False


def test_deactivate_missing_room(app):
    with app.app_context():
        assert deactivate_room(99999) is False
