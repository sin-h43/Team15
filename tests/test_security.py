from crb.app import create_app
from crb.db import init_db
from crb.seed import seed


def make_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "s.db"),
        "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
    })
    with app.app_context():
        init_db()
        seed()
    return app


def login_cookie(app):
    response = app.test_client().post("/login", data={"username": "employee1", "password": "emp123"})
    return response.headers["Set-Cookie"]


def test_every_response_has_the_basic_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_no_hsts_header_without_https(client):
    assert "Strict-Transport-Security" not in client.get("/").headers


def test_session_cookie_is_http_only_and_same_site(tmp_path, monkeypatch):
    monkeypatch.delenv("CRB_HTTPS", raising=False)
    cookie = login_cookie(make_app(tmp_path))
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" not in cookie


def test_https_mode_makes_the_cookie_secure_and_adds_hsts(tmp_path, monkeypatch):
    monkeypatch.setenv("CRB_HTTPS", "1")
    app = make_app(tmp_path)
    assert "Secure" in login_cookie(app)
    assert "Strict-Transport-Security" in app.test_client().get("/").headers
