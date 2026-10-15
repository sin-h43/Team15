from crb.audit import log_action
from crb.db import get_db


def add_entry(app):
    with app.app_context():
        log_action(get_db(), "admin1", "ROOM_CREATED", "room 9: Zeta")


def test_log_action_writes_a_row(app):
    add_entry(app)
    with app.app_context():
        row = get_db().execute("SELECT * FROM audit_log").fetchone()
    assert row["actor"] == "admin1"
    assert row["action"] == "ROOM_CREATED"
    assert row["detail"] == "room 9: Zeta"
    assert row["created_at"]


def test_visitor_is_sent_to_login(client):
    response = client.get("/audit")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_employee_cannot_read_the_audit_log(client, login):
    login("employee1", "emp123")
    assert client.get("/audit").status_code == 403


def test_auditor_can_read_the_audit_log(app, client, login):
    add_entry(app)
    login("auditor1", "aud123")
    response = client.get("/audit")
    assert response.status_code == 200
    assert b"ROOM_CREATED" in response.data


def test_admin_can_read_the_audit_log(app, client, login):
    add_entry(app)
    login("admin1", "admin123")
    response = client.get("/audit")
    assert response.status_code == 200
    assert b"room 9: Zeta" in response.data


def test_empty_audit_log_shows_a_message(client, login):
    login("auditor1", "aud123")
    assert b"No admin actions" in client.get("/audit").data
