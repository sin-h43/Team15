from datetime import datetime, timedelta

from crb.db import get_db
from crb.lockout import (
    LOCK_MINUTES,
    MAX_ATTEMPTS,
    TIME_FORMAT,
    is_locked,
    record_failure,
    reset_failures,
)

NOW = datetime(2030, 1, 15, 10, 0, 0)


def get_user(db):
    return db.execute("SELECT * FROM users WHERE username = 'employee1'").fetchone()


def fail_times(db, count):
    for _ in range(count):
        record_failure(db, get_user(db), NOW)


def test_new_user_is_not_locked(app):
    with app.app_context():
        assert is_locked(get_user(get_db()), NOW) is False


def test_failures_below_the_limit_do_not_lock(app):
    with app.app_context():
        db = get_db()
        fail_times(db, MAX_ATTEMPTS - 1)
        user = get_user(db)
        assert user["failed_attempts"] == MAX_ATTEMPTS - 1
        assert is_locked(user, NOW) is False


def test_reaching_the_limit_locks_the_account(app):
    with app.app_context():
        db = get_db()
        fail_times(db, MAX_ATTEMPTS)
        assert is_locked(get_user(db), NOW) is True


def test_lock_lasts_the_configured_minutes(app):
    with app.app_context():
        db = get_db()
        fail_times(db, MAX_ATTEMPTS)
        user = get_user(db)
        expected = (NOW + timedelta(minutes=LOCK_MINUTES)).strftime(TIME_FORMAT)
        assert user["locked_until"] == expected
        assert is_locked(user, NOW + timedelta(minutes=LOCK_MINUTES - 1)) is True
        assert is_locked(user, NOW + timedelta(minutes=LOCK_MINUTES + 1)) is False


def test_reset_clears_failures_and_lock(app):
    with app.app_context():
        db = get_db()
        fail_times(db, MAX_ATTEMPTS)
        reset_failures(db, get_user(db))
        user = get_user(db)
        assert user["failed_attempts"] == 0
        assert user["locked_until"] is None
