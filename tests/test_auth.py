from datetime import timedelta

from crb.auth import SESSION_MINUTES
from crb.db import get_db
from crb.lockout import MAX_ATTEMPTS


def wrong_passwords(login, count):
    for _ in range(count):
        login("employee1", "wrong-password")


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Log in" in response.data


def test_correct_password_redirects_to_home(login):
    response = login("employee1", "emp123")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_stores_user_and_role_in_session(client, login):
    login("admin1", "admin123")
    with client.session_transaction() as session:
        assert session["username"] == "admin1"
        assert session["role"] == "admin"
        assert session.permanent is True


def test_wrong_password_is_rejected(login):
    response = login("employee1", "wrong-password")
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_unknown_user_is_rejected(login):
    response = login("nobody", "whatever")
    assert response.status_code == 401


def test_session_lifetime_uses_the_configured_minutes(app):
    assert app.permanent_session_lifetime == timedelta(minutes=SESSION_MINUTES)


def test_repeated_wrong_passwords_lock_the_account(login):
    wrong_passwords(login, MAX_ATTEMPTS)
    response = login("employee1", "emp123")
    assert response.status_code == 403
    assert b"locked" in response.data


def test_one_failure_below_the_limit_does_not_lock(login):
    wrong_passwords(login, MAX_ATTEMPTS - 1)
    assert login("employee1", "emp123").status_code == 302


def test_successful_login_resets_the_failure_count(client, login):
    wrong_passwords(login, MAX_ATTEMPTS - 1)
    assert login("employee1", "emp123").status_code == 302
    client.post("/logout")
    wrong_passwords(login, MAX_ATTEMPTS - 1)
    assert login("employee1", "emp123").status_code == 302


def test_lock_ends_after_the_window(app, login):
    wrong_passwords(login, MAX_ATTEMPTS)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE users SET locked_until = '2000-01-01 00:00:00' WHERE username = 'employee1'")
        db.commit()
    assert login("employee1", "emp123").status_code == 302


def test_logout_clears_the_session(client, login):
    login("employee1", "emp123")
    response = client.post("/logout")
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "user_id" not in session
