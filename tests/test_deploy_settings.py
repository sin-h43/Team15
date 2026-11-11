"""Deployment safety: static files, startup guards, and one-time links never being logged."""
import pytest

from crb.app import create_app


def test_static_files_are_served_from_public(client):
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/live.js").status_code == 200


def test_serverless_host_without_database_url_refuses_to_start(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app()


def test_https_with_the_default_secret_key_refuses_to_start(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("CRB_SECRET_KEY", raising=False)
    monkeypatch.setenv("CRB_HTTPS", "1")
    with pytest.raises(RuntimeError, match="CRB_SECRET_KEY"):
        create_app()


def test_a_real_secret_key_lets_https_mode_start(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("CRB_HTTPS", "1")
    monkeypatch.setenv("CRB_SECRET_KEY", "x" * 40)
    assert create_app() is not None


def test_links_are_not_printed_when_real_email_is_on(app, capsys):
    app.config["TESTING"] = False
    app.config["CSRF_ENABLED"] = False
    app.config["RESEND_API_KEY"] = "re_test"
    import crb.mailer as mailer

    mailer_deliver = mailer.deliver
    mailer.deliver = lambda *args, **kwargs: None
    try:
        app.test_client().post("/forgot", data={"email": "employee1@crb.example"})
    finally:
        mailer.deliver = mailer_deliver
    assert "link for" not in capsys.readouterr().out
    with app.app_context():
        from crb.db import get_db
        assert get_db().execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1


def test_links_are_printed_for_local_use_without_real_email(app, capsys):
    app.config["TESTING"] = False
    app.config["CSRF_ENABLED"] = False
    app.test_client().post("/forgot", data={"email": "employee1@crb.example"})
    assert "reset link for employee1" in capsys.readouterr().out
