"""US-08 / CRB-F-011: equipment filter helper."""

from crb.equipment import filter_by_equipment, room_equipment


def _room(name, equipment):
    return {"name": name, "equipment": equipment}


ROOMS = [
    _room("Alpha", "whiteboard"),
    _room("Beta", "projector,whiteboard"),
    _room("Gamma", "projector,video_conf,whiteboard"),
    _room("Delta", "projector"),
    _room("Epsilon", "video_conf,whiteboard"),
    _room("Bare", ""),
]


def _names(rooms):
    return [room["name"] for room in rooms]


def test_room_lacking_required_projector_is_excluded():
    result = filter_by_equipment(ROOMS, ["projector"])
    assert _names(result) == ["Beta", "Gamma", "Delta"]


def test_room_must_have_all_required_items():
    result = filter_by_equipment(ROOMS, ["projector", "whiteboard"])
    assert _names(result) == ["Beta", "Gamma"]


def test_no_required_equipment_keeps_every_room():
    assert _names(filter_by_equipment(ROOMS, [])) == _names(ROOMS)


def test_room_with_no_equipment_is_excluded_when_something_required():
    result = filter_by_equipment(ROOMS, ["whiteboard"])
    assert "Bare" not in _names(result)


def test_no_room_has_requirement_returns_empty_list():
    only_whiteboards = [_room("Alpha", "whiteboard")]
    assert filter_by_equipment(only_whiteboards, ["video_conf"]) == []


def test_matching_ignores_case_and_spaces():
    rooms = [_room("Admin typed", " Projector , Whiteboard ")]
    assert _names(filter_by_equipment(rooms, ["projector"])) == ["Admin typed"]


def test_partial_name_does_not_match():
    rooms = [_room("Odd", "projector_screen")]
    assert filter_by_equipment(rooms, ["projector"]) == []


def test_room_equipment_returns_set_of_items():
    assert room_equipment(_room("Beta", "projector, whiteboard")) == {
        "projector",
        "whiteboard",
    }


def test_room_equipment_handles_empty_text():
    assert room_equipment(_room("Bare", "")) == set()


def test_filter_does_not_modify_input_list():
    rooms = list(ROOMS)
    filter_by_equipment(rooms, ["projector"])
    assert rooms == ROOMS


# --- through the search endpoint ---

SEARCH = {"date": "2026-11-01", "start": "09:00", "end": "10:00"}


def test_search_excludes_rooms_without_projector(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string=[*SEARCH.items(), ("equipment", "projector")],
    )
    names = [room["name"] for room in response.get_json()["rooms"]]
    assert names == ["Beta", "Gamma", "Delta"]


def test_search_with_two_equipment_items(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string=[
            *SEARCH.items(),
            ("equipment", "projector"),
            ("equipment", "video_conf"),
        ],
    )
    names = [room["name"] for room in response.get_json()["rooms"]]
    assert names == ["Gamma"]


def test_search_rejects_unknown_equipment(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string=[*SEARCH.items(), ("equipment", "hologram")],
    )
    assert response.status_code == 400