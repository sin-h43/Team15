from crb.equipment import has_all_equipment, split_equipment


def test_split_equipment_makes_a_list():
    assert split_equipment("projector,whiteboard") == ["projector", "whiteboard"]


def test_split_equipment_of_empty_text_is_empty_list():
    assert split_equipment("") == []


def test_room_with_every_wanted_item_matches():
    assert has_all_equipment("projector,whiteboard,video_conf", ["projector", "whiteboard"]) is True


def test_room_missing_one_wanted_item_does_not_match():
    assert has_all_equipment("projector", ["projector", "whiteboard"]) is False


def test_no_wanted_items_always_matches():
    assert has_all_equipment("", []) is True
