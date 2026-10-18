"""TEMPORARY integration tests for Sprint 1.

Each unit-test file checks one module on its own. These tests check that the
modules written by different people work together. They are deleted in Sprint 3
(commit "chore(test): remove temporary integration tests").
"""

from crb.db import get_db

DAY = {"date": "2030-01-15", "start": "10:00", "end": "11:00"}


def signed_in(app, username, password):
    """A brand-new browser that is already logged in."""
    client = app.test_client()
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 302
    return client


def search(client, **extra):
    query = dict(DAY)
    query.update(extra)
    return client.get("/rooms/search", query_string=query)


def test_visitor_is_sent_to_login_everywhere(app):
    client = app.test_client()
    for url in ["/rooms/search", "/admin/rooms", "/admin/blocks", "/audit"]:
        response = client.get(url)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_employee_logs_in_and_finds_the_seeded_rooms(app):
    employee = signed_in(app, "employee1", "emp123")
    response = search(employee)
    assert response.status_code == 200
    assert b"Alpha" in response.data
    assert b"Epsilon" in response.data


def test_employee_is_kept_out_of_admin_pages(app):
    employee = signed_in(app, "employee1", "emp123")
    for url in ["/admin/rooms", "/admin/blocks", "/audit"]:
        assert employee.get(url).status_code == 403


def test_room_added_by_admin_can_be_found_by_employee(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post(
        "/admin/rooms/new",
        data={"name": "Zeta", "location": "Pune", "capacity": "20", "equipment": ["projector"]},
    )
    employee = signed_in(app, "employee1", "emp123")
    response = search(employee, capacity="20")
    assert b"Zeta" in response.data
    assert b"Alpha" not in response.data


def test_deactivated_room_disappears_from_search(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post("/admin/rooms/1/deactivate")
    employee = signed_in(app, "employee1", "emp123")
    assert b"Alpha" not in search(employee).data
    assert b"Beta" in search(employee).data


def test_edited_equipment_changes_search_results(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post(
        "/admin/rooms/1/edit",
        data={"name": "Alpha", "location": "Bengaluru", "capacity": "4", "equipment": ["video_conf"]},
    )
    employee = signed_in(app, "employee1", "emp123")
    found = search(employee, equipment=["video_conf"], location="Bengaluru")
    assert b"Alpha" in found.data


def test_maintenance_block_hides_the_room_only_during_the_block(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post(
        "/admin/blocks/new",
        data={
            "room_id": "2",
            "start_time": "2030-01-15T10:00",
            "end_time": "2030-01-15T12:00",
            "reason": "Repair",
        },
    )
    employee = signed_in(app, "employee1", "emp123")
    during = employee.get(
        "/rooms/search", query_string={"date": "2030-01-15", "start": "10:30", "end": "11:30"}
    )
    after = employee.get(
        "/rooms/search", query_string={"date": "2030-01-15", "start": "12:00", "end": "13:00"}
    )
    assert b"Beta" not in during.data
    assert b"Beta" in after.data


def test_confirmed_booking_hides_the_room_from_search(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO bookings (room_id, user_id, start_time, end_time) VALUES (1, 1, ?, ?)",
            ("2030-01-15 10:00", "2030-01-15 11:00"),
        )
        db.commit()
    employee = signed_in(app, "employee1", "emp123")
    assert b"Alpha" not in search(employee).data


def test_auditor_sees_what_admin_did(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post(
        "/admin/blocks/new",
        data={
            "room_id": "2",
            "start_time": "2030-01-15T10:00",
            "end_time": "2030-01-15T12:00",
            "reason": "Repair",
        },
    )
    auditor = signed_in(app, "auditor1", "aud123")
    page = auditor.get("/audit")
    assert page.status_code == 200
    assert b"maintenance_block_created" in page.data


def test_locked_account_cannot_reach_protected_pages(app):
    client = app.test_client()
    for _ in range(5):
        client.post("/login", data={"username": "employee1", "password": "wrong"})
    locked = client.post("/login", data={"username": "employee1", "password": "emp123"})
    assert locked.status_code == 403
    assert client.get("/rooms/search").status_code == 302