"""US-09 / CRB-F-010: search by location, capacity, equipment and time.

Seed data used here:
    Alpha    Bengaluru   4  whiteboard
    Beta     Bengaluru   8  projector,whiteboard
    Gamma    Bengaluru  12  projector,video_conf,whiteboard
    Delta    Pune        6  projector
    Epsilon  Pune       10  video_conf,whiteboard
"""

from crb.db import get_db

DAY = "2026-11-01"


def _room_id(name):
    return get_db().execute(
        "SELECT id FROM rooms WHERE name = ?", (name,)
    ).fetchone()["id"]


def _book(room_name, start, end, status="confirmed"):
    db = get_db()
    user_id = db.execute(
        "SELECT id FROM users WHERE username = 'employee1'"
    ).fetchone()["id"]
    db.execute(
        "INSERT INTO bookings (room_id, user_id, start_time, end_time, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (_room_id(room_name), user_id, f"{DAY} {start}", f"{DAY} {end}", status),
    )
    db.commit()


def _block(room_name, start, end):
    db = get_db()
    db.execute(
        "INSERT INTO maintenance_blocks (room_id, start_time, end_time, reason) "
        "VALUES (?, ?, ?, 'Maintenance')",
        (_room_id(room_name), f"{DAY} {start}", f"{DAY} {end}"),
    )
    db.commit()


def _search(client, start="10:00", end="11:00", **filters):
    """Call the JSON search and return the matching room names."""
    params = [("date", DAY), ("start", start), ("end", end)]
    for key, value in filters.items():
        if isinstance(value, list):
            params.extend((key, item) for item in value)
        else:
            params.append((key, value))
    response = client.get("/api/rooms/search", query_string=params)
    assert response.status_code == 200
    return [room["name"] for room in response.get_json()["rooms"]]


def test_no_filters_returns_every_free_active_room(client, login):
    login("employee1", "emp123")
    assert _search(client) == ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]


def test_all_filters_together_return_only_matching_free_room(client, login, app):
    login("employee1", "emp123")
    with app.app_context():
        _book("Beta", "10:00", "11:00")  # matches filters but is taken

    names = _search(
        client,
        location="Bengaluru",
        capacity="8",
        equipment=["projector"],
    )
    assert names == ["Gamma"]


def test_inactive_room_is_not_returned(client, login, app):
    login("employee1", "emp123")
    with app.app_context():
        get_db().execute("UPDATE rooms SET active = 0 WHERE name = 'Gamma'")
        get_db().commit()

    assert "Gamma" not in _search(client)
    assert _search(client, location="Bengaluru", capacity="12") == []


def test_room_with_maintenance_block_is_not_returned(client, login, app):
    login("employee1", "emp123")
    with app.app_context():
        _block("Delta", "10:30", "12:00")

    assert "Delta" not in _search(client, location="Pune")


def test_cancelled_booking_does_not_hide_room(client, login, app):
    login("employee1", "emp123")
    with app.app_context():
        _book("Delta", "10:00", "11:00", status="cancelled")

    assert "Delta" in _search(client, location="Pune")


def test_back_to_back_booking_keeps_room_in_results(client, login, app):
    login("employee1", "emp123")
    with app.app_context():
        _book("Delta", "09:00", "10:00")  # ends exactly when search starts
        _book("Epsilon", "11:00", "12:00")  # starts exactly when search ends

    names = _search(client, location="Pune")
    assert names == ["Delta", "Epsilon"]


def test_location_filter_ignores_case(client, login):
    login("employee1", "emp123")
    assert _search(client, location="pune") == ["Delta", "Epsilon"]


def test_capacity_is_a_minimum(client, login):
    login("employee1", "emp123")
    assert _search(client, capacity="10") == ["Gamma", "Epsilon"]


def test_location_capacity_and_equipment_combine(client, login):
    login("employee1", "emp123")
    names = _search(
        client,
        location="Pune",
        capacity="8",
        equipment=["video_conf", "whiteboard"],
    )
    assert names == ["Epsilon"]


def test_no_room_matches_returns_empty_list(client, login):
    login("employee1", "emp123")
    assert _search(client, location="Mumbai") == []


def test_search_page_lists_matching_rooms(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/rooms/search",
        query_string={
            "date": DAY,
            "start": "10:00",
            "end": "11:00",
            "location": "Pune",
        },
    )
    assert response.status_code == 200
    assert b"Delta" in response.data
    assert b"Epsilon" in response.data
    assert b"Alpha" not in response.data


def test_search_page_says_when_nothing_matches(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/rooms/search",
        query_string={
            "date": DAY,
            "start": "10:00",
            "end": "11:00",
            "location": "Mumbai",
        },
    )
    assert response.status_code == 200
    assert b"No matching rooms found." in response.data


def test_search_requires_login(client):
    response = client.get(
        "/api/rooms/search",
        query_string={"date": DAY, "start": "10:00", "end": "11:00"},
    )
    assert response.status_code == 302


def test_search_without_a_time_range_is_rejected(client, login):
    login("employee1", "emp123")
    response = client.get("/api/rooms/search", query_string={"location": "Pune"})
    assert response.status_code == 400