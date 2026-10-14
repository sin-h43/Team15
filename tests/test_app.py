from crb.app import create_app
from crb.db import get_db


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Conference Room Booking" in response.data


def test_home_page_asks_visitor_to_log_in(client):
    assert b"log in" in client.get("/").data


def test_unknown_page_returns_404(client):
    assert client.get("/no-such-page").status_code == 404


def test_init_db_command_creates_demo_data(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "cli.db"),
            "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",  # fast hashing, tests only
        }
    )
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert "Database ready" in result.output
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 3