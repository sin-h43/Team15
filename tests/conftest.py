import pytest

from crb.app import create_app
from crb.db import init_db
from crb.seed import seed


@pytest.fixture
def app(tmp_path):
    """A fresh app with its own empty database and the demo data."""
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",  # fast hashing, tests only
        }
    )
    with app.app_context():
        init_db()
        seed()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    """Call login("admin1", "admin123") to sign in the test client."""

    def do_login(username, password):
        return client.post("/login", data={"username": username, "password": password})

    return do_login