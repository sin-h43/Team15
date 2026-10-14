
from crb.blocks_repo import (
    create_block,
    delete_block,
    get_block,
    list_blocks,
)
from crb.rooms_repo import create_room


def test_create_and_get_block(app):
    with app.app_context():
        room_id = create_room("Meeting Room", "Floor 1", 10)
        block_id = create_block(
            room_id,
            "2026-10-20T09:00",
            "2026-10-20T11:00",
            "Air conditioning repair",
        )

        block = get_block(block_id)

        assert block["room_id"] == room_id
        assert block["start_time"] == "2026-10-20T09:00"
        assert block["end_time"] == "2026-10-20T11:00"
        assert block["reason"] == "Air conditioning repair"


def test_get_missing_block(app):
    with app.app_context():
        assert get_block(99999) is None


def test_list_blocks(app):
    with app.app_context():
        room_id = create_room("Meeting Room", "Floor 1", 10)
        create_block(room_id, "2026-10-20T09:00", "2026-10-20T10:00", "Repair")
        create_block(room_id, "2026-10-21T09:00", "2026-10-21T10:00", "Cleaning")

        blocks = list_blocks()

        assert len(blocks) == 2
        assert blocks[0]["start_time"] <= blocks[1]["start_time"]


def test_list_blocks_filters_by_room(app):
    with app.app_context():
        room_a = create_room("Room A", "Floor 1", 10)
        room_b = create_room("Room B", "Floor 2", 8)

        create_block(room_a, "2026-10-20T09:00", "2026-10-20T10:00", "Repair")
        create_block(room_b, "2026-10-20T11:00", "2026-10-20T12:00", "Cleaning")

        blocks = list_blocks(room_a)

        assert len(blocks) == 1
        assert blocks[0]["room_id"] == room_a


def test_delete_block(app):
    with app.app_context():
        room_id = create_room("Meeting Room", "Floor 1", 10)
        block_id = create_block(
            room_id, "2026-10-20T09:00", "2026-10-20T10:00", "Repair"
        )

        assert delete_block(block_id) is True
        assert get_block(block_id) is None


def test_delete_missing_block(app):
    with app.app_context():
        assert delete_block(99999) is False
