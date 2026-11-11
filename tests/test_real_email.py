"""Phase 3: real email through the mail service, rate limits, and the cron endpoint.

The mail service is replaced by a fake, so no test ever touches the network.
"""
import json
import urllib.error

import pytest

from crb.db import get_db
from crb.notifications import send_email
from tests.helpers import make_user


class FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def mail(app, monkeypatch):
    """Turn real mail on with a fake service; `calls` collects what would have been sent."""
    app.config["RESEND_API_KEY"] = "re_test_key"
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append({
            "url": request.full_url,
            "auth": request.get_header("Authorization"),
            "body": json.loads(request.data.decode()),
        })
        return FakeResponse()

    monkeypatch.setattr("crb.mailer.urllib.request.urlopen", fake_urlopen)
    return calls


def outbox(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM outbox ORDER BY id").fetchall()


def test_email_is_sent_to_the_users_real_address(app, mail):
    make_user(app, "priya", "x" * 10)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE users SET email = 'priya@example.org' WHERE username = 'priya'")
        db.commit()
        send_email(db, "priya", "Hello", "Body text")
    assert len(mail) == 1
    assert mail[0]["url"] == "https://api.resend.com/emails"
    assert mail[0]["auth"] == "Bearer re_test_key"
    assert mail[0]["body"]["to"] == ["priya@example.org"]
    assert mail[0]["body"]["subject"] == "Hello" and mail[0]["body"]["text"] == "Body text"
    assert outbox(app)[0]["status"] == "sent"


def test_demo_example_addresses_are_never_sent(app, mail):
    with app.app_context():
        send_email(get_db(), "employee1", "Hello", "Body")
    assert mail == []
    assert outbox(app)[0]["status"] == "stored"


def test_without_a_key_nothing_is_sent(app, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr("crb.mailer.urllib.request.urlopen", boom)
    with app.app_context():
        send_email(get_db(), "employee1", "Hello", "Body")
    assert outbox(app)[0]["status"] == "stored"


def test_a_failed_send_is_recorded_and_does_not_break_the_booking(app, monkeypatch):
    app.config["RESEND_API_KEY"] = "re_test_key"

    def down(request, timeout=None):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("crb.mailer.urllib.request.urlopen", down)
    make_user(app, "priya", "x" * 10)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE users SET email = 'priya@example.org' WHERE username = 'priya'")
        db.commit()
        send_email(db, "priya", "Hello", "Body")  # must not raise
    assert outbox(app)[0]["status"] == "failed"


def test_service_error_status_counts_as_failed(app, monkeypatch):
    app.config["RESEND_API_KEY"] = "re_test_key"

    def rejected(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 422, "bad", {}, None)

    monkeypatch.setattr("crb.mailer.urllib.request.urlopen", rejected)
    make_user(app, "priya", "x" * 10)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE users SET email = 'priya@example.org' WHERE username = 'priya'")
        db.commit()
        send_email(db, "priya", "Hello", "Body")
    assert outbox(app)[0]["status"] == "failed"


def test_one_address_gets_at_most_three_reset_emails_an_hour(app):
    client = app.test_client()
    for _ in range(5):
        assert client.post("/forgot", data={"email": "employee1@crb.example"}).status_code == 200
    assert len(outbox(app)) == 3


def test_one_network_address_is_limited_to_ten_requests_an_hour(app):
    client = app.test_client()
    codes = [client.post("/forgot", data={"email": "a%d@example.org" % n}).status_code for n in range(12)]
    assert codes[:10] == [200] * 10 and codes[10:] == [429, 429]


def test_cron_is_off_without_a_secret(app):
    assert app.test_client().get("/cron/send-reminders").status_code == 404


def test_cron_needs_the_right_secret_and_runs_the_jobs(app):
    app.config["CRON_SECRET"] = "s3cret"
    client = app.test_client()
    assert client.get("/cron/send-reminders").status_code == 401
    assert client.get("/cron/send-reminders", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get("/cron/send-reminders", headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200
    assert ok.get_json() == {"reminders_sent": 0, "holds_released": 0}


def test_the_mail_services_reason_is_logged_for_a_refusal(app, monkeypatch, caplog):
    import io

    app.config["RESEND_API_KEY"] = "re_test_key"

    def refused(request, timeout=None):
        body = io.BytesIO(b'{"message": "You can only send testing emails to your own email address"}')
        raise urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, body)

    monkeypatch.setattr("crb.mailer.urllib.request.urlopen", refused)
    make_user(app, "priya", "x" * 10)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE users SET email = 'priya@example.org' WHERE username = 'priya'")
        db.commit()
        send_email(db, "priya", "Hello", "Body")
    assert "403: You can only send testing emails" in caplog.text
    assert "re_test_key" not in caplog.text
    assert outbox(app)[0]["status"] == "failed"
