from crb.db import get_db


def test_search_page_requires_login(client):
    response = client.get("/rooms/search")
    assert response.status_code == 302


def test_employee_can_open_search_page(client, login):
    login("employee1", "emp123")
    response = client.get("/rooms/search")
    assert response.status_code == 200
    assert b"Search Available Rooms" in response.data


def test_json_search_returns_matching_rooms(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string={
            "date": "2026-11-01",
            "start": "09:00",
            "end": "10:00",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "rooms" in data
    assert any(room["name"] == "Alpha" for room in data["rooms"])


def test_search_filters_by_location_and_capacity(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string={
            "date": "2026-11-01",
            "start": "09:00",
            "end": "10:00",
            "location": "Bengaluru",
            "capacity": "8",
        },
    )

    assert response.status_code == 200
    rooms = response.get_json()["rooms"]
    assert all("Bengaluru" in room["location"] for room in rooms)
    assert all(room["capacity"] >= 8 for room in rooms)


def test_search_filters_by_equipment(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string=[
            ("date", "2026-11-01"),
            ("start", "09:00"),
            ("end", "10:00"),
            ("equipment", "projector"),
        ],
    )

    assert response.status_code == 200
    rooms = response.get_json()["rooms"]
    assert all(
        "projector" in room["equipment"].split(",")
        for room in rooms
    )


def test_search_rejects_invalid_time_range(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string={
            "date": "2026-11-01",
            "start": "11:00",
            "end": "10:00",
        },
    )
    assert response.status_code == 400


def test_search_rejects_invalid_capacity(client, login):
    login("employee1", "emp123")
    response = client.get(
        "/api/rooms/search",
        query_string={
            "date": "2026-11-01",
            "start": "09:00",
            "end": "10:00",
            "capacity": "invalid",
        },
    )
    assert response.status_code == 400


def test_search_excludes_room_during_maintenance(client, login, app):
    login("employee1", "emp123")

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
                "Maintenance",
            ),
        )
        db.commit()

    response = client.get(
        "/api/rooms/search",
        query_string={
            "date": "2026-11-01",
            "start": "10:00",
            "end": "10:30",
        },
    )

    assert response.status_code == 200
    rooms = response.get_json()["rooms"]
    assert all(room["id"] != room_id for room in rooms)