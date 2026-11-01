import pytest
from cryptography.fernet import InvalidToken

from crb.crypto import decrypt_text, encrypt_text


def test_round_trip(app):
    with app.app_context():
        assert decrypt_text(encrypt_text("ravi@crb.example")) == "ravi@crb.example"


def test_stored_text_is_not_readable(app):
    with app.app_context():
        token = encrypt_text("ravi@crb.example")
    assert "ravi" not in token
    assert "crb.example" not in token


def test_same_text_gives_a_different_token_each_time(app):
    with app.app_context():
        assert encrypt_text("same") != encrypt_text("same")


def test_text_with_accents_survives(app):
    with app.app_context():
        assert decrypt_text(encrypt_text("Zoë Müller")) == "Zoë Müller"


def test_a_different_key_cannot_read_the_token(app):
    with app.app_context():
        token = encrypt_text("secret")
    app.config["SECRET_KEY"] = "another-key"
    with app.app_context():
        with pytest.raises(InvalidToken):
            decrypt_text(token)


def test_pii_key_overrides_the_secret_key(app):
    with app.app_context():
        token = encrypt_text("secret")
    app.config["PII_KEY"] = "a-separate-key"
    with app.app_context():
        with pytest.raises(InvalidToken):
            decrypt_text(token)
