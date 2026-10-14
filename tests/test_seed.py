from flask import Flask
from werkzeug.security import check_password_hash

from crb.db import close_db, get_db, init_db
from crb.seed import seed


def make_seeded_app(tmp_path):
    app = Flask("crb")
    app.config["DATABASE"] = str(tmp_path / "test.db")
    app.config["PASSWORD_HASH_METHOD"] = "pbkdf2:sha256:1000"  # fast hashing, tests only
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
        seed()
    return app


def test_seed_adds_three_users_and_five_rooms(tmp_path):
    app = make_seeded_app(tmp_path)
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 5


def test_seeded_users_have_the_three_roles(tmp_path):
    app = make_seeded_app(tmp_path)
    with app.app_context():
        rows = get_db().execute("SELECT role FROM users ORDER BY id").fetchall()
    assert [row["role"] for row in rows] == ["employee", "admin", "auditor"]


def test_seeded_password_is_stored_as_a_hash(tmp_path):
    app = make_seeded_app(tmp_path)
    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE username = 'admin1'").fetchone()
    assert user["password_hash"] != "admin123"
    assert check_password_hash(user["password_hash"], "admin123")