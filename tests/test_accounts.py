"""Self-signup, email confirmation, password reset, user roles (Phase 2)."""
import re

from crb.db import get_db
from tests.helpers import signed_in

SIGNUP = {"username": "priya", "email": "Priya@Example.com", "password": "longenough1", "confirm": "longenough1"}


def query(app, sql, params=()):
    with app.app_context():
        return get_db().execute(sql, params).fetchall()


def last_link(app, path):
    """The newest emailed link containing `path` (e.g. /verify/)."""
    for row in query(app, "SELECT body FROM outbox ORDER BY id DESC"):
        found = re.search(r"http://localhost(" + re.escape(path) + r"\S+)", row["body"])
        if found:
            return found.group(1)
    raise AssertionError("no email with " + path)


def sign_up(app, client=None, **overrides):
    client = client or app.test_client()
    return client, client.post("/signup", data={**SIGNUP, **overrides})


def test_signup_creates_unconfirmed_employee_and_sends_link(app):
    client, response = sign_up(app)
    assert response.status_code == 200 and b"Check your email" in response.data
    user = query(app, "SELECT * FROM users WHERE username = 'priya'")[0]
    assert user["role"] == "employee" and user["email"] == "priya@example.com"
    assert not user["email_verified"]
    assert "/verify/" in query(app, "SELECT body FROM outbox")[0]["body"]


def test_cannot_log_in_until_email_is_confirmed(app):
    client, _ = sign_up(app)
    response = client.post("/login", data={"username": "priya", "password": "longenough1"})
    assert response.status_code == 403 and b"confirm your email" in response.data
    assert client.get(last_link(app, "/verify/")).status_code == 200
    ok = client.post("/login", data={"username": "priya@example.com", "password": "longenough1"})
    assert ok.status_code == 302


def test_confirmation_link_works_once(app):
    client, _ = sign_up(app)
    link = last_link(app, "/verify/")
    assert client.get(link).status_code == 200
    assert client.get(link).status_code == 400


def test_signup_rejects_weak_password_bad_email_and_taken_name(app):
    assert sign_up(app, password="short", confirm="short")[1].status_code == 400
    assert sign_up(app, email="not-an-email")[1].status_code == 400
    assert sign_up(app, confirm="different1")[1].status_code == 400
    assert sign_up(app, username="Employee1")[1].status_code == 400
    assert query(app, "SELECT COUNT(*) AS n FROM users WHERE username = 'priya'")[0]["n"] == 0


def test_signup_with_registered_email_gives_same_answer_and_creates_nothing(app):
    sign_up(app)
    _, response = sign_up(app, username="priya2")
    assert response.status_code == 200 and b"Check your email" in response.data
    assert query(app, "SELECT COUNT(*) AS n FROM users WHERE username = 'priya2'")[0]["n"] == 0


def test_password_reset_flow(app):
    client = app.test_client()
    client.post("/forgot", data={"email": "employee1@crb.example"})
    link = last_link(app, "/reset/")
    assert client.get(link).status_code == 200
    bad = client.post(link, data={"password": "brandnew123", "confirm": "nope"})
    assert bad.status_code == 400
    assert client.post(link, data={"password": "brandnew123", "confirm": "brandnew123"}).status_code == 200
    assert client.post(link, data={"password": "again12345", "confirm": "again12345"}).status_code == 400
    assert client.post("/login", data={"username": "employee1", "password": "emp123"}).status_code == 401
    assert client.post("/login", data={"username": "employee1", "password": "brandnew123"}).status_code == 302


def test_forgot_password_does_not_reveal_unknown_addresses(app):
    client = app.test_client()
    known = client.post("/forgot", data={"email": "employee1@crb.example"})
    unknown = client.post("/forgot", data={"email": "nobody@nowhere.org"})
    assert known.status_code == unknown.status_code == 200
    assert b"on its way" in unknown.data
    assert query(app, "SELECT COUNT(*) AS n FROM outbox")[0]["n"] == 1


def test_expired_token_is_rejected(app):
    from datetime import datetime, timedelta

    from crb.tokens import issue_token, find_token_user

    with app.app_context():
        db = get_db()
        raw = issue_token(db, 1, "reset", now=datetime.now() - timedelta(hours=2))
        assert find_token_user(db, raw, "reset") is None


def test_only_admin_can_open_user_page_and_change_roles(app):
    assert signed_in(app, "employee1", "emp123").get("/admin/users").status_code == 403
    admin = signed_in(app, "admin1", "admin123")
    page = admin.get("/admin/users")
    assert page.status_code == 200 and b"employee1" in page.data
    assert admin.post("/admin/users/1/role", data={"role": "auditor"}).status_code == 302
    assert query(app, "SELECT role FROM users WHERE id = 1")[0]["role"] == "auditor"
    log = query(app, "SELECT actor, action FROM audit_log")[0]
    assert (log["actor"], log["action"]) == ("admin1", "USER_ROLE_CHANGED")


def test_admin_cannot_change_own_role_or_set_unknown_role(app):
    admin = signed_in(app, "admin1", "admin123")
    admin.post("/admin/users/2/role", data={"role": "employee"})
    admin.post("/admin/users/1/role", data={"role": "superuser"})
    roles = {r["id"]: r["role"] for r in query(app, "SELECT id, role FROM users")}
    assert roles[2] == "admin" and roles[1] == "employee"


def test_attendee_can_be_invited_by_email_but_not_before_confirmation(app):
    from crb.attendees import AttendeeError, add_attendee
    from tests.helpers import make_booking
    import pytest

    booking_id = make_booking(app)
    sign_up(app)
    with app.app_context():
        db = get_db()
        with pytest.raises(AttendeeError):
            add_attendee(db, booking_id, "priya@example.com")
        db.execute("UPDATE users SET email_verified = 1 WHERE username = 'priya'")
        db.commit()
        add_attendee(db, booking_id, "priya@example.com")


def test_create_user_command_makes_a_confirmed_admin(app):
    result = app.test_cli_runner().invoke(
        args=["create-user", "--username", "boss", "--email", "boss@example.com", "--role", "admin"],
        input="strongpass1\nstrongpass1\n",
    )
    assert result.exit_code == 0, result.output
    user = query(app, "SELECT role, email_verified FROM users WHERE username = 'boss'")[0]
    assert user["role"] == "admin" and user["email_verified"]
