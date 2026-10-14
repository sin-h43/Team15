import pytest

from crb.app import create_app
from crb.db import get_db, init_db
from crb.seed import seed


@pytest.fixture
def app(tmp_path):
    database = tmp_path / "test_admin.db"

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(database),
        }
    )

    with app.app_context():
        init_db()
        seed()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, role="admin"):
    users = {
        "admin": (2, "admin"),
        "employee": (1, "employee"),
        "auditor": (3, "auditor"),
    }
    user_id, user_role = users[role]

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = user_role


def room_form(**overrides):
    data = {
        "name": "Test Room",
        "location": "Bengaluru",
        "capacity": "6",
        "equipment": "projector",
    }
    data.update(overrides)
    return data


def test_admin_rooms_requires_login(client):
    response = client.get("/admin/rooms")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("role", ["employee", "auditor"])
def test_admin_rooms_rejects_non_admin(client, role):
    login_as(client, role)
    response = client.get("/admin/rooms")
    assert response.status_code == 403


def test_admin_can_view_rooms(client):
    login_as(client)
    response = client.get("/admin/rooms")
    assert response.status_code == 200
    assert b"Alpha" in response.data


def test_admin_can_open_new_room_form(client):
    login_as(client)
    response = client.get("/admin/rooms/new")
    assert response.status_code == 200


def test_admin_can_create_room(client, app):
    login_as(client)
    response = client.post("/admin/rooms/new", data=room_form())

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/rooms")

    with app.app_context():
        db = get_db()
        room = db.execute(
            "SELECT * FROM rooms WHERE name = ?",
            ("Test Room",),
        ).fetchone()
        assert room is not None
        assert room["capacity"] == 6


def test_create_room_rejects_empty_name(client, app):
    login_as(client)
    response = client.post(
        "/admin/rooms/new",
        data=room_form(name=""),
    )

    assert response.status_code == 400

    with app.app_context():
        db = get_db()
        room = db.execute(
            "SELECT * FROM rooms WHERE name = ?",
            ("",),
        ).fetchone()
        assert room is None


def test_create_room_rejects_invalid_capacity(client):
    login_as(client)
    response = client.post(
        "/admin/rooms/new",
        data=room_form(capacity="not-a-number"),
    )
    assert response.status_code == 400


def test_admin_can_edit_room(client, app):
    login_as(client)

    with app.app_context():
        room_id = get_db().execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]

    response = client.post(
        f"/admin/rooms/{room_id}/edit",
        data=room_form(name="Alpha Updated"),
    )

    assert response.status_code == 302

    with app.app_context():
        room = get_db().execute(
            "SELECT name FROM rooms WHERE id = ?",
            (room_id,),
        ).fetchone()
        assert room["name"] == "Alpha Updated"


def test_edit_missing_room_returns_404(client):
    login_as(client)
    response = client.get("/admin/rooms/99999/edit")
    assert response.status_code == 404


def test_admin_can_deactivate_room(client, app):
    login_as(client)

    with app.app_context():
        room_id = get_db().execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]

    response = client.post(f"/admin/rooms/{room_id}/deactivate")
    assert response.status_code == 302

    with app.app_context():
        room = get_db().execute(
            "SELECT active FROM rooms WHERE id = ?",
            (room_id,),
        ).fetchone()
        assert room["active"] == 0


def test_deactivate_missing_room_returns_404(client):
    login_as(client)
    response = client.post("/admin/rooms/99999/deactivate")
    assert response.status_code == 404


def test_admin_can_view_maintenance_blocks(client):
    login_as(client)
    response = client.get("/admin/blocks")
    assert response.status_code == 200
    assert b"Maintenance Blocks" in response.data


def test_admin_can_create_maintenance_block(client, app):
    login_as(client)

    with app.app_context():
        room_id = get_db().execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]

    response = client.post(
        "/admin/blocks/new",
        data={
            "room_id": str(room_id),
            "start_time": "2026-11-01T09:00",
            "end_time": "2026-11-01T10:00",
            "reason": "Electrical maintenance",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        block = get_db().execute(
            "SELECT * FROM maintenance_blocks WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        assert block is not None
        assert block["reason"] == "Electrical maintenance"


def test_maintenance_block_rejects_invalid_time_order(client, app):
    login_as(client)

    with app.app_context():
        room_id = get_db().execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]

    response = client.post(
        "/admin/blocks/new",
        data={
            "room_id": str(room_id),
            "start_time": "2026-11-01T11:00",
            "end_time": "2026-11-01T10:00",
            "reason": "Maintenance",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        count = get_db().execute(
            "SELECT COUNT(*) FROM maintenance_blocks"
        ).fetchone()[0]
        assert count == 0


def test_maintenance_block_rejects_inactive_room(client, app):
    login_as(client)

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

    response = client.post(
        "/admin/blocks/new",
        data={
            "room_id": str(room_id),
            "start_time": "2026-11-01T09:00",
            "end_time": "2026-11-01T10:00",
            "reason": "Maintenance",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        count = get_db().execute(
            "SELECT COUNT(*) FROM maintenance_blocks"
        ).fetchone()[0]
        assert count == 0


def test_admin_can_delete_maintenance_block(client, app):
    login_as(client)

    with app.app_context():
        db = get_db()
        room_id = db.execute(
            "SELECT id FROM rooms WHERE name = 'Alpha'"
        ).fetchone()["id"]
        cursor = db.execute(
            """
            INSERT INTO maintenance_blocks
                (room_id, start_time, end_time, reason)
            VALUES (?, ?, ?, ?)
            """,
            (
                room_id,
                "2026-11-01T09:00",
                "2026-11-01T10:00",
                "Test maintenance",
            ),
        )
        block_id = cursor.lastrowid
        db.commit()

    response = client.post(f"/admin/blocks/{block_id}/delete")
    assert response.status_code == 302

    with app.app_context():
        block = get_db().execute(
            "SELECT * FROM maintenance_blocks WHERE id = ?",
            (block_id,),
        ).fetchone()
        assert block is None


def test_delete_missing_block_returns_404(client):
    login_as(client)
    response = client.post("/admin/blocks/99999/delete")
    assert response.status_code == 404
